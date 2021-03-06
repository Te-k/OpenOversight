# Contributing Guide

First, thanks for being interested in helping us out! If you find an issue you're interested in, feel free to make a comment about how you're thinking of approaching implementing it in the issue and we can give you feedback. 

## Submitting a PR

When you come to implement your new feature, you should branch off `develop` and add commits to implement your feature. If your git history is not so clean, please do rewrite before you submit your PR - if you're not sure if you need to do this, go ahead and submit and we can let you know when you submit. 

## Development Environment

Our standard development environment is an Ubuntu 14 VM. We manage it with Vagrant, which means you'll need Vagrant and Virtualbox installed to start out.

Make sure that vagrant and Virtualbox are installed, and then run:

`vagrant up`

This creates a new, pristine virtual machine and provisions it to be an almost-copy of production with a local test database. (Behind the scenes, this is all happening via the files in vagrant/puppet.) If everything works, you should get a webserver listening at `http://localhost:3000` you can browse to on your host machine. In addition, you can now SSH into it:

`vagrant ssh`

The provisioning step creates a virtual environment (venv) in `~/oovirtenv`. If you will be running lots of python-related commands, you can 'activate' the virtual environment (override the built-in python and pip commands and add pytest and fab to your path) by activating it:
```
vagrant@vagrant-ubuntu-trusty-64:~$ source /home/vagrant/oovirtenv/bin/activate
(oovirtenv)vagrant@vagrant-ubuntu-trusty-64:~$
```
When this is done, you no longer need to preface python commands (as below) with `~/oovirtenv/bin`.

The app, as provisioned, is running under gunicorn, which means that it does not dynamically reload your changes.

If you run the app in debug mode, you can see these changes take effect on every update, but certain changes will kill the server in a way some of us find really irritating. To do this:

`vagrant ssh` (if you're not already there)
```
$ sudo service gunicorn stop
 * Stopping Gunicorn workers
 [oo] *
vagrant@vagrant-ubuntu-trusty-64:~$ cd /vagrant/OpenOversight/
vagrant@vagrant-ubuntu-trusty-64:/vagrant$ ~/oovirtenv/bin/python ./run.py
 * Running on http://127.0.0.1:3000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
```

You can access your PostgreSQL development database via psql using:

`psql  -h localhost -d openoversight-dev -U openoversight --password`

with the password `terriblepassword`.

The provisioning step already does this, but in case you need it, in the `/vagrant/OpenOversight` directory, there is a script to create the database:

`~/oovirtenv/bin/python create_db.py`

If the database doesn't already exist, `create_db.py` will set it up.

In the event that you need to create or delete the test data, you can do that with
`~/oovirtenv/bin/python test_data.py --populate` to create the data
or
`~/oovirtenv/bin/python test_data.py --cleanup` to delete the data

## Running Unit Tests

 Run tests with `pytest`:

`~/oovirtenv/bin/pytest`

## Migrating the Database

If you e.g. add a new column or table, you'll need to migrate the database. You can use:

`~/oovirtenv/bin/python migrate_db.py`

to do this.
`~/oovirtenv/bin/python upgrade_db.py` and `~/oovirtenv/bin/python downgrade_db.py` can also be used as necessary. Note that we followed [this tutorial](http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database) to set this up.

## Changing the Development Environment

If you're making massive changes to the development environment provisioning, you should know that Vagrant and the Puppet modules that provision the box use Ruby, so you'll want some reasonably-modern Ruby. Anything in the 2.0-2.2 area should work. Puppet has some annoying interactions where puppet 3 doesn't work with ruby 2.2, though, so you might have to get creative on modern OSes.

If you don't have bundler installed:

`gem install bundler`

If you don't have rake installed:

`bundle install`

Then provision the VM:

`rake vagrant:provision`

Puppet modules are dropped into place by librarian-puppet, and there's a rake task that'll do it without the headache of remembering all the paths and such:

`rake vagrant:build_puppet`
