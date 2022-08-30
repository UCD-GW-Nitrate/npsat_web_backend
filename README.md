# npsat_web
Web Interface for the NPSAT tool

See Confluence for internal notes on how we deployed this


## Model Runs
This backend code has a slightly convoluted process for handling runs, but it makes sense based
on the other design constraints. The main Django code accepts parameters for a new run over the 
ModelRun API interface. It logs these parameters to the database for a ModelRun.

A django management command `process_runs` must be running in the background - it is set up this
way since it needs its own event loop to be able to manage a queue and send commands to the Mantis
server and load results. It will pull new runs from the database and send them to Mantis,
then load results in the database when they come back. ModelRun.running and ModelRun.complete
will be set appropriately to reflect the status of a ModelRun. An API endpoint can provide
this status so the frontend can query whether results are available, then query for results
when they are ready (or maybe if it queries for status and status is "complete" it gets the
results back too to save additional querying)


## Server Test Procedure

One must follow the following steps in order to test run the server in local development environment
1. Run Mantis Server: Change directory to /Mantis/Data, then use MantisServer executable to run mantisConfig.ini with the following command: </Mantis/CPP/MantisServer/MantisServer/MantisServer.exe -c mantisConfig.ini>
2. In a seperate terminak, change directory to npsat_web_backend, run command <Python3 manage.py runserver 8010>. When the server started, login Django administration in your local browser with link "localhost:8010/admin". Find MantisServer Object and manually set its port to '1234', and set its status to 'online'. Once the above steps are done, restart the server (important step not to be skipped).
3. In a seperate terminal, change directory to npsat_web_backend, run command <Python3 manage.py process_runs> to start the processor
4. In a seperate terminal, change directory to npsat_web_frontend_v2 and run command <npm start>. DEBUG: If the complilation fails due to JavaScript Heap Memory Leak, set the memory parameter to a larger number (for example 4GB) by running command <export NODE_OPTIONS="--max-old-space-size=4096"> before <npm start>

## Set Super User and Load Initial Data
1. Super User: Super user allows you to test the server with the highest administrative privileges. To set super user, run command in npsat_web_backend <Python3 manage.py createsuperuser>, then set username and password by following the prompts.
2. Load Initial Data: Initial data need to be loaded before server is started. In npsat_web_backend, run command <Python3 manage.py load_initial_data>. If the initial data is loaded repeatedly, run command <Python3 manage.py flush> first to clear up the old data in the cache. 