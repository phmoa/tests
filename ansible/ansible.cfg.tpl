[defaults]
# SSH timeout
timeout = 9000
roles_path = {{ rootdir }}/ansible/roles
fact_caching_timeout=9000
fact_caching_connection={{ rootdir }}/ansible/inventory
filter_plugins = {{ rootdir }}/ansible/plugins/filters
remote_tmp = /tmp/.ansible-${USER}/tmp
host_key_checking = False
ansible_user = "{{ username }}"
ansible_become_pass = "{{ password }}"
localhost_warning = False
display_skipped_hosts = false
library ={{ rootdir }}/ansible/library
result_format=yaml
COLLECTIONS_PATH={{ rootdir }}/.env/lib/python3.12/site-packages/
local_tmp = /tmp/.ansible/tmp

[inventory]
enable_plugins = host_list, script, auto, yaml, ini
cache = True
cache_plugin = yaml


[ssh_connection]
ssh_args = -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPersist=30m -o StrictHostKeyChecking=no -o GSSAPIKeyExchange=no -o GSSAPIAuthentication=no
control_path_dir = /tmp/.ansible/cp
