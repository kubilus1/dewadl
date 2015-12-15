# dewadl
Turn WADL descriptions into Python APIs


Note:  dewadl was written specifically to take advantage of the uDeploy WADL interface.  Your mileage may vary when using this against other WADL interfaces!

## Useage

dewadl provides several use case:  CLI mode, API mode, interactive mode.

### CLI mode

Lists all options.  (See Configuration below)

    $ ./dewadl.py -h 

Lists all available commands for the WADL you are using
    $ ./dewadl.py help

Run a command, perhaps providing arguments

    $ ./dewadly.py <CMD> [arg1 ... argN]


### API mode

How about a generic use case:

    from dewadl import dewadl

    myapi = dewadl.wadl_processor(wadl_file="localfile.wadl")

    myapi.doStuff()

If we were to use this with a remote uDeploy server:

    from dewadl import dewadl

    ucd = dewadl.wadl_processor(wadl_url="https://myucdserver.com/rest/application.wadl", userid="myuser", passwd="mypass")

    apps = ucd.getActiveApplications()
    for app in apps:
        print app.id, app.name


### Interactive mode

It may be useful to be able to interactively explore API commands.  To run dewadl in interactive mode, use the -i parameter.

    $ ./dewadl.py -i

    -----------------------------

    Welcome to DeWADL Python interface!.
    'wadl' object has been created.

    W) 

This provides all available commands under the 'wadl' object with tab completion.

    W) wadl.getActive
    wadl.getActiveAgentPools(                   wadl.getActiveComponentTemplateComponents(  wadl.getActiveResourcesWithAgentByPath(     wadl.getActiveVersionsByEnvironment(        
    wadl.getActiveApplications(                 wadl.getActiveComponentTemplates(           wadl.getActiveTagsForType(        

Use standard python 'help' to get info on a particular command:

    W) help(wadl.getApplication)
    Help on function getApplication in module __main__:

    getApplication(*args, **kwds)
        getApplication accepts arguments: ['id']


## Configuration

If you get tired of entering URLs and passwords you may setup a configuration file of the following format:


    [dewadl]
    weburl=<MY URL>
    userid=<MY USERID>
    password=<MY PASSWORD>

Dewadl will look for a configuration file in the following order:

    1.  ./.dewadl
    2.  /etc/dewadl.cfg
    3.  ~/.dewadl

Note if a password is not provided in the configuration file or on the command line, the user will be prompted.
