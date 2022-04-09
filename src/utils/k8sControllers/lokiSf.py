from kubernetes import client, config


class LokiSf:
    def __init__(self,
                 lk_name,
                 lk_namespace,
                 lk_image,
                 lk_limits,
                 lk_requests,
                 lk_labels,
                 lk_replicas,
                 lk_storage,
                 lk_uid):

        """ Create the Loki StatefulSet
        :param lk_name: The Loki Name defined on metadata.name Field of CRD
        :param lk_namespace: The Loki Namespace defined on metadata.namespace
        :param lk_image: The Loki Image defined on spec.image Field of CRD
        :param lk_limits: The Limits defined on spec.resources.limits of CRD
        :param lk_requests: The Requests defined on spec.resources.requests of CRD
        :param lk_labels: The Labels defined on metadata.labels of CRD
        :param lk_replicas: The Replicas defined on spec.replicas of CRD
        :param lk_storage: The Storage request defined on spec.storage of CRD
        :param lk_uid: The UID defined on metadata.uid of CRD
        """

        self.name = lk_name
        self.namespace = lk_namespace
        self.image = lk_image
        self.api = client.AppsV1Api()
        self.limits = lk_limits
        self.replicas = lk_replicas
        self.requests = lk_requests
        self.labels = lk_labels
        self.storage = lk_storage
        self.uid = lk_uid
        self.container_port = 3100

        self.probes = self.__Probes(container_port=self.container_port)
        config.load_incluster_config()

    # Define and return the resources object
    def __resources(self):
        rc = client.V1ResourceRequirements(
            limits=self.limits,
            requests=self.requests
        )
        return rc

    # Define and return the Ports object
    def __ports(self) -> list:
        port = client.V1ContainerPort(
            container_port=self.container_port,
            name='http-metrics',
            protocol='TCP'
        )
        # The V1ContainerPort Object must be a list
        _port = list()
        _port.append(port)
        return _port

    # Define the container Object
    def __define_container(self) -> list:
        ct = client.V1Container(
            name=self.name,
            image=self.image,
            image_pull_policy="IfNotPresent",
            # liveness_probe=self.probes.liveness(),
            # readiness_probe=self.probes.readiness(),
            resources=self.__resources(),  # Get the Resources Object returned by the function
            ports=self.__ports(),  # Get the Ports object returned by the function
            volume_mounts=[
                client.V1VolumeMount(
                    mount_path='/etc/loki',
                    name='config'
                ),
                client.V1VolumeMount(
                    mount_path='/etc/loki/rules',
                    name='rules'
                ),
                client.V1VolumeMount(
                    mount_path='/data',
                    name='data'
                )
            ]
        )
        # The V1Container Object must be a list
        _ct = list()
        _ct.append(ct)
        return _ct

    # Define the Pod object
    def __pod(self):
        pod = client.V1PodSpec(
            containers=self.__define_container(),  # Get the container list returned by the function
            volumes=[
                client.V1Volume(
                    name='config',
                    config_map=client.V1ConfigMapVolumeSource(
                        name='loki-config',
                        default_mode=420
                    )
                ),
                client.V1Volume(
                    name='rules',
                    config_map=client.V1ConfigMapVolumeSource(
                        name='logs-alert',
                        default_mode=420
                    )
                ),
                # TODO: TEMPORARY
                client.V1Volume(
                    name='data',
                    empty_dir=client.V1EmptyDirVolumeSource()
                )
            ]
        )
        return pod

    # Define the Pod Template Object
    def __pod_template(self):
        pod_tpl = client.V1PodTemplateSpec(
            spec=self.__pod(),  # Get the Pod returned by the function
            metadata=client.V1ObjectMeta(  # Define the object metadata
                name=self.name,
                namespace=self.namespace,
                labels=self.labels
            )
        )
        return pod_tpl

    def __data_pvc(self):
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name='data'),
            spec=client.V1PersistentVolumeClaimSpec(
                resources=client.V1ResourceRequirements(
                    requests={'storage': self.storage}
                ),
                access_modes=['ReadWriteOnce']
            )
        )
        _pvc = list()
        _pvc.append(pvc)
        return _pvc

    # Define the StatefulSet Spec Object
    def __stateful_set_spec(self):
        st_spec = client.V1StatefulSetSpec(
            service_name='teste',
            replicas=self.replicas,
            template=self.__pod_template(),  # Get the Pod Template Object returned by the function
            selector=client.V1LabelSelector(
                match_labels=self.labels
            )
            # volume_claim_templates=self.__data_pvc()
        )
        return st_spec

    def __obj_owner(self):
        _owner = list()
        st_owner = client.V1OwnerReference(
            api_version="jack.experts/v1",
            block_owner_deletion=True,
            controller=True,
            kind="Loki",
            name=self.name,
            uid=self.uid
        )

        _owner.append(st_owner)

        return _owner

    # Define the StatefulSet Object
    def stateful_set(self):
        st = client.V1StatefulSet(
            spec=self.__stateful_set_spec(),  # Get the StatefulSet Spec Object returned by the function
            metadata=client.V1ObjectMeta(  # Define the Metadata Object
                name=self.name,
                namespace=self.namespace,
                labels=self.labels,
                owner_references=self.__obj_owner()
            )
        )

        return st

    # Inner Class to define the liveness and Readiness Probes
    class __Probes:
        def __init__(self, container_port):
            self.initial_delay_seconds = 45
            self.timeout_seconds = 1
            self.period_seconds = 10
            self.success_threshold = 1
            self.failure_threshold = 3
            self.container_port = container_port

        @staticmethod
        def __http_get(path: str, port: int, scheme: str):
            http_get = client.V1HTTPGetAction(
                path=path,
                port=port,
                scheme=scheme
            )

            return http_get

        def liveness(self):
            ln = client.V1Probe(
                initial_delay_seconds=self.initial_delay_seconds,
                timeout_seconds=self.timeout_seconds,
                period_seconds=self.period_seconds,
                success_threshold=self.success_threshold,
                failure_threshold=self.failure_threshold,
                http_get=self.__http_get(path='/ready', scheme='HTTP', port=self.container_port)
            )
            return ln

        def readiness(self):
            rn = client.V1Probe(
                initial_delay_seconds=self.initial_delay_seconds,
                timeout_seconds=self.timeout_seconds,
                period_seconds=self.period_seconds,
                success_threshold=self.success_threshold,
                failure_threshold=self.failure_threshold,
                http_get=self.__http_get(path='/ready', scheme='HTTP', port=self.container_port)
            )
            return rn
