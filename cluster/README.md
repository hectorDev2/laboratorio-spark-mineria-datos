# Clúster Spark local multiproceso

Este laboratorio levanta **cuatro procesos JVM independientes** en una sola Mac:

- Spark Master: RPC `127.0.0.1:7077`, UI `127.0.0.1:8080`.
- Worker 1: RPC `7078`, UI `8081`, 1 core, 768 MiB.
- Worker 2: RPC `7079`, UI `8082`, 1 core, 768 MiB.
- Worker 3: RPC `7080`, UI `8083`, 1 core, 768 MiB.

La dirección del clúster es `spark://127.0.0.1:7077`. Todos los servicios quedan ligados a loopback: no son accesibles desde otras computadoras.

## Requisitos verificados para este equipo

- macOS sobre Apple Silicon.
- Java 21.
- Python 3.12.
- Spark/PySpark 4.2.0.
- `lsof`, incluido en macOS.

Los scripts también detectan `SPARK_HOME` desde la instalación de PySpark. Si Spark está instalado por otro medio, exportá su ruta antes de empezar:

```bash
export SPARK_HOME=/ruta/a/spark
```

## Uso

Desde este directorio:

```bash
chmod +x *.sh tests/*.sh
./preflight.sh
./setup_data.sh
./start.sh
./status.sh
```

Abrí `http://127.0.0.1:8080` y verificá que aparezcan tres workers vivos. Las interfaces individuales están en los puertos `8081`, `8082` y `8083`.

`start.sh` acepta opcionalmente `1`, `2` o `3` para iniciar únicamente esa cantidad de workers. Esto permite ejecutar los escenarios de escalabilidad sin editar scripts:

```bash
./stop.sh
./start.sh 1
```

Para ejecutar una aplicación PySpark:

```bash
./submit.sh ../scripts/mi_aplicacion.py --argumento valor
```

Durante la ejecución, la interfaz de la aplicación queda en `http://127.0.0.1:4040`. Al terminar:

```bash
./stop.sh
./status.sh
```

## Datos

`setup_data.sh` crea enlaces simbólicos en `cluster/data/` hacia los dos CSV ubicados en la raíz del proyecto. Esto evita duplicar aproximadamente 150 MB. Para copiar los archivos físicamente:

```bash
./setup_data.sh --copy
```

También se puede indicar un directorio distinto:

```bash
./setup_data.sh /ruta/con/los/csv
```

## Archivos operativos

Al iniciar se crea `cluster/runtime/`:

- `pids/`: PID de cada proceso; permite detener únicamente el proceso correcto.
- `logs/`: salida separada de master y workers.
- `work/`: directorio independiente para cada worker.

Si un puerto está ocupado, `preflight.sh --for-start` cancela el arranque y muestra el proceso que escucha. `stop.sh` valida la clase Java antes de enviar señales, para no terminar un proceso ajeno si un PID fue reutilizado.

## Recursos y límites

Los tres workers reservan como máximo 2.25 GiB en conjunto. El envío usa 1 GiB para el driver, 512 MiB por executor y un máximo de tres cores. Esta distribución deja margen al sistema operativo en una Mac con 8 GiB.

Este montaje permite observar planificación, registro de workers, executors y distribución de tareas entre procesos. No mide rendimiento de red ni tolerancia a la pérdida de una máquina física, porque todos los procesos comparten hardware, memoria, disco y sistema operativo.

## Diagnóstico

```bash
./preflight.sh
./status.sh
tail -n 80 runtime/logs/master.log
tail -n 80 runtime/logs/worker-1.log
```

Si un inicio quedó interrumpido, ejecutá `./stop.sh`, revisá los puertos con `./status.sh` y repetí `./start.sh`. No borres archivos PID mientras los procesos estén activos.

## Validación sin iniciar servicios

```bash
bash tests/test_cluster_files.sh
```

La validación comprueba estructura, sintaxis Bash, JSON y la asignación de puertos y recursos. No genera capturas ni resultados de ejecución.
