import logging
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

# config.load_kube_config('/lixo/kubernetes/jac/kubeconfig-production.yaml')
config.load_incluster_config()
api = client.AppsV1Api()


def update(name: str, namespace: str, new_resource: dict, ):
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": name,
                            "resources": new_resource
                        }
                    ]
                }
            }
        }
    }

    try:
        _patch = api.patch_namespaced_stateful_set(
            namespace=namespace,
            name=name,
            body=patch
        )
        logging.info(f"\n\n\tSuccess Update!\n\n")
    except ApiException as e:
        logging.error(f"{e}")


def __calc_resource(namespace: str, name: str):
    up_mem = 3
    pkg = dict()
    api = client.CustomObjectsApi()
    loki = api.get_namespaced_custom_object(
        group='jack.experts',
        version='v1',
        namespace=namespace,
        plural='lokis',
        name=name
    )

    resource = loki['spec']['resources']

    memory = loki['spec']['resources']['limits']['memory']
    #
    if 'Mi' in memory:
        num = int(memory.split('Mi')[0]) + up_mem
        _num = str(num) + 'Mi'
        resource['limits']['memory'] = _num
        pkg["spec"] = {"resources": resource}
        return pkg
    elif 'Gi' in memory:
        num = int(memory.split('Gi')[0]) + up_mem
        _num = str(num) + 'Gi'
        resource['limits']['memory'] = _num
        pkg["spec"] = {"resources": resource}
        return pkg


def vpa(name: str, namespace: str):
    _event = client.CoreV1Api()
    response = _event.read_namespaced_pod(namespace=namespace, name=f'{name}-0')
    evento = _event.api_client.sanitize_for_serialization(response)

    current_status = evento['status']['containerStatuses'][0]['state']
    last_status = evento['status']['containerStatuses'][0]['lastState']

    logging.info(f"\n\n\t{__calc_resource(namespace, name)}\n\n")

    if 'waiting' in current_status:  # Verify current container status
        # If the current status is waiting, verify if the Last Status is terminated
        if 'terminated' in last_status:
            api = client.CustomObjectsApi()
            api.patch_namespaced_custom_object(
                group="jack.experts",
                version="v1",
                namespace=namespace,
                plural="lokis",
                name=name,
                body=__calc_resource(name=name, namespace=namespace)
            )
            logging.info("\n\nVPA WORKS\n\n")


