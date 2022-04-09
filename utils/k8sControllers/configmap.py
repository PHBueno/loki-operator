import logging
import yaml
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


class ConfigMap:
    def __init__(self, namespace, name):
        self.name = name
        self.namespace = namespace
        self.api = client.CoreV1Api()
        config.load_incluster_config()
        # config.load_kube_config('/lixo/kubernetes/jac/kubeconfig-production.yaml')

    # Method to verify if ConfigMap exists
    def __verify(self) -> bool:
        try:
            self.api.read_namespaced_config_map(name=self.name, namespace=self.namespace)
            return True
        except ApiException as e:
            logging.error(f'{e}')
            return False

    # Method to add a new key on ConfigMap
    def new_key_cm(self, key_name, data):

        new_data = client.V1ConfigMap(
            data={f'{key_name}.yaml': yaml.dump(data)}
        )
        try:
            __new_key = self.api.patch_namespaced_config_map(
                name=self.name,
                namespace=self.namespace,
                body=new_data
            )
            logging.info(f"\n\n\tThe key {key_name} was successfully added!\n\n")
            return __new_key
        except ApiException as e:
            logging.error(e)

    # Method to create a ConfigMap if not exists
    def create_cm(self):
        check = self.__verify()

        # If ConfigMap not Exists, then create
        if check is False:
            # Define Metadata to ConfigMap
            meta = client.V1ObjectMeta(
                name=self.name,
                namespace=self.namespace
            )

            # Construct the ConfigMap
            configmap = client.V1ConfigMap(
                metadata=meta,
                data={}
            )
            # Apply
            try:
                created = self.api.create_namespaced_config_map(
                    namespace=self.namespace,
                    body=configmap
                )
                logging.info("\n\n\tThe ConfigMap was Successfully created!\n\n")
                return created
            except ApiException as e:
                logging.error(e)

        else:
            logging.info("\n\n\tThe ConfigMap exists!\n\n")




