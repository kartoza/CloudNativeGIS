## Quick installation

### Production

```
git submodule update
git clone https://github.com/kartoza/CloudNativeGIS
cp deployment/.template.env deployment/.env
cp deployment/docker-compose.override.template deployment/docker-compose.template
make up
```

The web will be available at `http://127.0.0.1/`

To stop containers:

```
make kill
```

To stop and delete containers:

```
make down
```

### Install as django library

This application can be installed as django library.

To install it, put `git+https://github.com/kartoza/CloudNativeGIS.git` to
requirements.<br>
Add `cloud_native_gis` to INSTALLED_APPS,<br>
and add url `path('', include('cloud_native_gis.urls'))`.

### Development

```
git submodule update
git clone https://github.com/kartoza/CloudNativeGIS
cp deployment/.template.env deployment/.env
cp deployment/docker-compose.override.template deployment/docker-compose.template
```

After that, do

- open new terminal
- on folder root of project, do

```
make serve
```

Wait until it is done
when there is sentence "webpack xxx compiled successfully in xxx ms".<br>
After that, don't close the terminal.
If it is accidentally closed, do `make serve` again

Next step:

- Open new terminal
- Do commands below

```
make up
make dev
```

Wait until it is on.

The web can be accessed using `http://localhost:5000/`

If the web is taking long time to load, restart cloud_native_gis_dev_1
container.<br>
The sequence should be `make dev`, after that run or restart
cloud_native_gis_dev_1.

### Maputnik updates

CloudNativeGIS using maputnik to edit style.
We could update maputnik in the folder root/maputnik.
Maputnik can be accessed in the django-admin and layers, and there is "editor"
column that will be redirect to maputnik instance.
By default, it is using maputnik production.

To change and test maputnik:

```
make serve-maputnik
```

After it is done, there will be link to maputnik.
Copy the link and paste in:
go to deployment/.env
change MAPUTNIK_URL to the copied link

```
restart dev container
```

After done, we need to update the maputnik production.<br>
First, create commit of maputnik and push it to repo.
Then

```
make build-maputnik
```

It will create files in the
django_project/cloud_native_gis/templates/maputnik.html
and also assets in the django_project/cloud_native_gis/static

After that, test it by remove MAPUTNIK_URL and restart dev container.
If satisfied, just create commit for the changes.