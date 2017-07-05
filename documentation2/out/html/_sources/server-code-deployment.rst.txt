.. _server-code-deployment:

==============================
New code or scripts deployment
==============================

.. toctree::
    :maxdepth: 2


How to deploy new or changed script to the server
=================================================
1. Commit new code to global GitHub site
2. :ref:`Log in <basic-server-management>` to the server
3. Make sure that your actual branch on GitHub is equal to active branch on the server
    * ``cd`` to project working directory with .git
        **Repositories paths**

        * ``/var/data/notebooks`` - Jupyter notebooks GIT directory
        * ``/var/data/tmqrengine`` - framework GIT directory (including main code, trading scripts, settings, etc.)

    * Run command ``git status``
        Possible command output::

            root@tmqr-quant:/var/data/tmqrengine# git status
            On branch payoff_diagrams
            Your branch is up-to-date with 'origin/payoff_diagrams'.
            Untracked files:
            <list of untracked files>

    .. note:: If branch name is differs from ``master`` it would be better to ask project lead for assistance.
4. Pull changed files from GitHub repository by running ``git pull`` command (it will ask GitHub account credentials)
5. If you change trading scripts or settings or core file it requires reboot of online trading scripts and Jupyter notebook server.
    .. warning:: Don't forget to save your work before framework restarting.

    **To reboot** the framework and trading scripts run ``service supervisor restart`` command.

Executing long running tasks on the server
==========================================
The main problem with execution of long-running tasks via SSH is in task halt when the SSH connection is closed in some reasons.
If you need to execute long-running task or script like EXO backfilling or Alpha rebalancing you need to utilize ``tmux`` command.
Tmux is opening new long-living session in the background even when SSH is disconnected.

To launch new session just type ``tmux``, to attach to existing session run ``tmux attach``. To minimize the current Tmux session to background hit ``ctlr+b and then d``, you can always
return to this session typing ``tmux attach``.


Indices and tables
==================

* :ref:`index-page`
