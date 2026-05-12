# Local OpenStack Control Plane

이 디렉터리는 외부 OpenStack tenant가 없을 때, 로컬 LXD 컨테이너 안에 DevStack 기반
OpenStack control plane을 올리는 bootstrap 스크립트를 제공합니다.

이 단계가 성공하면 이후 `infra/private-cloud/openstack` Terraform은 생성된 OpenStack API에
붙어서 network, subnet, security group, key pair, VM node group을 만들 수 있습니다.

## 실행

```sh
infra/private-cloud/openstack-local/bootstrap-devstack.sh
```

기본값:

- LXD 컨테이너: `ha-openstack`
- 이미지: `ubuntu:24.04`
- DevStack branch: `master`
- 로컬 admin password: `hybrid-ai-devstack`

환경 변수로 조정할 수 있습니다.

```sh
HA_OPENSTACK_CONTAINER=ha-openstack \
HA_DEVSTACK_BRANCH=master \
HA_DEVSTACK_PASSWORD=hybrid-ai-devstack \
infra/private-cloud/openstack-local/bootstrap-devstack.sh
```

## 결과 파일

성공하면 아래 파일이 생성됩니다.

```txt
.ha/openstack-local/openrc.sh
.ha/handoff/local-openstack.env
```

Terraform/OpenStack CLI를 사용할 때는 다음처럼 로드합니다.

```sh
source .ha/openstack-local/openrc.sh
```

## 주의

DevStack은 개발/검증용 OpenStack입니다. production OpenStack 배포에는 Kolla-Ansible,
Canonical OpenStack/Sunbeam, OpenStack-Ansible 같은 별도 배포 방식을 사용해야 합니다.
