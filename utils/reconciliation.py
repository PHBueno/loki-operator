
import re
import logging
from kubernetes import config, client
from .k8sControllers.lokiSf import LokiSf


class Reconciliation:
    def __init__(self, cr_group, cr_version, cr_plural):
        """ Run the reconciliation for Loki Resources
        :param cr_group: The CustomResource Group
        :param cr_version: The CustomResource Version
        :param cr_plural: The CustomResource Plural Name
        """

        self.sts_queue = list()
        self.cr_group = cr_group
        self.cr_version = cr_version
        self.cr_plural = cr_plural

        self.custom_resources_api = client.CustomObjectsApi()
        self.apps_api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()
        config.load_incluster_config()
        # config.load_kube_config('/lixo/kubernetes/jac/kubeconfig-production.yaml')

    def __get_crds(self):
        """ Get Loki CRDs from all namespaces """

        crds = dict()
        _crds = self.custom_resources_api.list_cluster_custom_object(
            group=self.cr_group,
            plural=self.cr_plural,
            version=self.cr_version
        )

        for item in _crds['items']:
            crds[item['metadata']['name']+'/'+item['metadata']['namespace']] = item

        return crds

    def __get_stateful_set(self, name, namespace):
        """ Get Loki StatefulSet representation """
        stateful_set = self.apps_api.read_namespaced_stateful_set(
            name=name,
            namespace=namespace
        )

        json_stateful_set = self.core_api.api_client.sanitize_for_serialization(stateful_set)

        return json_stateful_set

    @staticmethod
    def __clear_defaults_field_sts(statefulset):
        """ Clear de Default Fields from Statefulset """
        metadata_fields = ['creationTimestamp',
                           'selfLink',
                           'uid',
                           'resourceVersion',
                           'managedFields']

        # Find and remove default cattle annotations
        if 'annotations' in statefulset['spec']['template']['metadata']:
            pattern_annotation = ".*cattle*."
            pattern = re.compile(pattern_annotation)
            discard_annotation = [
                key for key, value in statefulset['spec']['template']['metadata']['annotations'].items()
                if pattern.match(key)
            ]

            for annotation in discard_annotation:
                statefulset['spec']['template']['metadata']['annotations'].pop(annotation)

            # Verify if annotations have more inside fields
            if not bool(statefulset['spec']['template']['metadata']['annotations']):
                statefulset['spec']['template']['metadata'].pop('annotations')  # If not, delete the annotations field

        # Remove metadata fields
        for field in metadata_fields:
            if field in statefulset['metadata'].keys():
                statefulset['metadata'].pop(field)

        if 'securityContext' in statefulset['spec']['template']['spec']['containers'][0]:
            if not bool(statefulset['spec']['template']['spec']['containers'][0]['securityContext']['capabilities']):
                statefulset['spec']['template']['spec']['containers'][0].pop('securityContext')

        statefulset.pop('status')

        return statefulset

    def compare_resources(self):
        """ Get Loki StatefulSet from all namespaces """

        lk_crd = self.__get_crds()
        for item, value in lk_crd.items():
            name, namespace = item.split('/')

            old_sts = self.__clear_defaults_field_sts(self.__get_stateful_set(name=name, namespace=namespace))

            lk = LokiSf(
                lk_name=f"{value['metadata']['name']}-new",
                lk_namespace=value['metadata']['namespace'],
                lk_image=value['spec']['image'],
                lk_requests=value['spec']['resources']['requests'],
                lk_limits=value['spec']['resources']['limits'],
                lk_labels=value['metadata']['labels'],
                lk_storage=value['spec']['storage'],
                lk_uid=value['metadata']['uid']
            )

            new_sts = lk.stateful_set()

            dry_run = self.apps_api.create_namespaced_stateful_set(
                namespace=namespace,
                body=new_sts,
                dry_run='All'
            )

            new_sts_json = self.core_api.api_client.sanitize_for_serialization(dry_run)

            # Update fields
            new_sts_json['spec']['template']['metadata']['name'] = value['metadata']['name']
            new_sts_json['spec']['template']['spec']['containers'][0]['name'] = value['metadata']['name']
            new_sts_json['metadata']['name'] = value['metadata']['name']
            new_sts_json['metadata']['generation'] = old_sts['metadata']['generation']

            new_sts_json = self.__clear_defaults_field_sts(new_sts_json)
            return new_sts_json == old_sts
            # try:
            #     if not new_sts_json == old_sts:
            #         # self.apps_api.patch_namespaced_stateful_set(
            #         #     name=value['metadata']['name'],
            #         #     namespace=value['metadata']['namespace'],
            #         #     body=new_sts_json
            #         # )
            #         # logging.info("\n\n\treconciliate\n\n")
            #         # logging.info(f"\n\n\tNEW: {new_sts_json}\n\n")
            #         # logging.info(f"\n\n\tACTUAL{old_sts}\n\n")
            # except Exception as e:
            #     logging.error(e)
            # logging.info(f"\n\n\tNEW: {new_sts_json}\n\n")
            # logging.info(f"\n\n\tACTUAL{old_sts}\n\n")
