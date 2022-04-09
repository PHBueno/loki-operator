# # # # # # # # # # # # # # # # # # # # #
# Author: Pedro Henrique da Silva Bueno #
# Date:   09/02/2022                    #
# # # # # # # # # # # # # # # # # # # # #

import logging
import kopf
import asyncio
import typing

# Kubernetes Client imports
from kubernetes import client
from kubernetes.client.exceptions import ApiException

# Internal Imports
from utils.k8sControllers.configmap import ConfigMap
from utils.k8sControllers.lokiSf import LokiSf
from utils.resources import update, vpa
from utils.reconciliation import Reconciliation

# TODO: Utilizar @kopf.on.timer() para reconciliação dos recursos

# TODO: Ferificar como utilizar VPA para CPU

cm_name_rule = 'logs-alert'
cm_ns = 'loki-operator'

log_alert = ConfigMap(namespace=cm_ns, name=cm_name_rule)


async def tunnel(fn: kopf.WebhookFn) -> typing.AsyncIterator[kopf.WebhookClientConfig]:
    service = kopf.WebhookClientConfigService(
        namespace='loki-operator',
        name='loki-operator-webhook',
        port=8080,
        path='/test'
    )

    client_config = kopf.WebhookClientConfig(
        service=service
    )

    yield client_config
    await asyncio.Event().wait()


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    # settings.admission.server = kopf.WebhookServer(
    #     addr='0.0.0.0',
    #     port=8080,
    #     host='loki-operator-webhook.loki-operator.svc.cluster.local',
    #     extra_sans=['loki-operator-webhook.loki-operator.svc']
    # )
    settings.admission.server = tunnel
    settings.admission.managed = 'teste.jack.webhook'

#
# @kopf.on.validate('statefulset', labels={'operated': 'True'}, operation='UPDATE')
# def validate(body, headers, warnings, **_):
#     logging.info(headers)
#     raise kopf.AdmissionError(f"\n\n\tTest: Body {headers}\n\n")
#
#
# @kopf.on.mutate('Loki', operation='CREATE')
# def labels(patch, **_):
#     patch.meta['labels'] = {'operated': 'True'}  # Add label on create to identify the resource


# Create Loki Resource
@kopf.on.create('Loki')
async def create_fn(body, spec, name, namespace, **kwargs):
    api = client.AppsV1Api()

    loki = LokiSf(
        lk_name=name,
        lk_namespace=namespace,
        lk_image=spec['image'],
        lk_limits=spec['resources']['limits'],
        lk_requests=spec['resources']['requests'],
        lk_labels=body['metadata']['labels'],
        lk_storage=spec['storage'],
        lk_uid=body['metadata']['uid'],
        lk_replicas=spec['replicas']
    )

    sf_loki = loki.stateful_set()

    try:
        log_alert.create_cm()
        api.create_namespaced_stateful_set(
            body=sf_loki,
            namespace=namespace
        )

        # logging.info(f"\n\n\t{sf_loki}\n\n")
        logging.info("\n\nLoki was created\n\n")
    except ApiException as e:
        logging.error(e)


# Update Loki resources
@kopf.on.field('loki', field='spec.resources')
async def resources_change(new, body, **kwargs):
    update(name=body['metadata']['name'], namespace=body['metadata']['namespace'], new_resource=new)


@kopf.on.create('logalert')
async def create_la(body, name, namespace, **kwargs):

    __cm = log_alert.new_key_cm(name, body['spec'])


# @kopf.timer('Loki', interval=10.0)
# def reconciliation(spec, name, namespace, **kwargs):
#     rec = Reconciliation(
#         cr_group='jack.experts',
#         cr_plural='lokis',
#         cr_version='v1'
#     )

    # rec.compare_resources()
# @kopf.timer('Loki', interval=30.0)
# async def resources(spec, name, namespace, **kwargs):
#     vpa(name, namespace)
