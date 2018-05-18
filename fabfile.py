from fabric.api import task, local, lcd


@task
def start_redis():
    local('sudo /etc/init.d/redis-server start')

@task
def stop_redis():
    local('sudo /etc/init.d/redis-server stop')

@task
def start_router():
    local("LOG_CFG=conf/router_log_config.yaml gunicorn --daemon 'router.router_app:loader()' --error-logfile gunicorn.log --access-logfile gunicorn_access.log")

@task
def stop_router():
    local("pkill -f 'router.router_app'")

@task
def start_ipynb():
    with lcd('examples'):
        local('LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 ipython notebook --ip="*"')
