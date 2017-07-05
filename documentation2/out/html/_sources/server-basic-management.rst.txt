.. _basic-server-management:

Basic server management
***********************

.. toctree::
    :maxdepth: 2


This section describes common task for remote server management and diagnostics.


Logging in
==========
The server is managed over SSH session, to establish SSH session do next steps:

1. Connect to the server via OpenVPN
2. Open or install SSH client
    * **Linux / MacOS** - just open terminal window
    * **Windows** - `Install PuTTY <https://tartarus.org/~simon/putty-snapshots/x86/putty-installer.msi>`_
3. Login to server ``10.0.1.2`` using username: **tmqrquant** and password
    * **Linux / MacOS** - type ``ssh tmqrquant@10.0.1.2``
    * **Windows** - enter username and password when prompted
4. Elevate permissions to **root** user (i.e. super admin)
    Type ``sudo su`` and re-enter password for user **tmqrquant**, after that you should see commant prompt like that: ``root@tmqr-quant:/home/tmqrquant#``


Common server paths and commands
================================
Common commands
---------------
* ``ls`` - show directory files
* ``cd`` - change directory (i.e. ``cd /var/data/``, changes current working directory to ``/var/data/``
* ``mc`` - user friendly file manager like old Norton Commander

Server diagnostics commands
---------------------------
* ``htop`` - text GUI server resource monitoring and process management (for memory and CPU load analysis)
* ``supervisorctl status`` - shows the status of execution for trading scripts, Jupyter server and web server

Useful server paths
-------------------
* ``/var/data/notebooks`` - Jupyter notebooks GIT directory
* ``/var/data/tmqrengine`` - framework GIT directory (including main code, trading scripts, settings, etc.)
* ``/var/data/mongodb`` - MongoDB storage files
* ``/etc/`` - settings directory for entire system

Logs path
---------
* ``/var/log/syslog`` - generic system log file
* ``/var/log/supervisor`` - generic Supervisor service logs
* ``/var/log/rabbitmq`` - RabbitMQ logs
* ``/var/log/mongodb`` - MongoDB logs
* ``/var/data/tmqrengine/scripts/logs`` - TMQR Framework logs, also available via ``http://10.0.1.2:8080/``


Basic service management commands
---------------------------------
Following commands should be executed by ``root`` or via ``sudo <command>``

* ``service rabbitmq-server start|stop|restart`` - Start/stop of RabbitMQ service (used for inter-script communication)
* ``service mongod start|stop|restart`` - Start/stop of MongoDB service
* ``service supervisor start|stop|restart`` - Start/stop of Supervisor service which is managing all trading scripts
* ``reboot`` - restarts the server





Indices and tables
==================

* :ref:`index-page`

