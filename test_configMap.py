from kubernetes import client, config
#
config.load_kube_config('/lixo/kubernetes/jac/kubeconfig-production.yaml')

api = client.CustomObjectsApi()




