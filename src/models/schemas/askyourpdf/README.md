## Run Alembic Migrations

### Configuration
```bash
sudo apt install alembic
```

```bash
cp alembic.ini.example alembic.ini
```

- Update the `alembic.ini` with your database credentials (`sqlalchemy.url`)
  
### (Optional) Create a new migration

```bash
alembic revision --autogenerate -m "Add ..."
```

### Upgrade the database

```bash
alembic upgrade head
```