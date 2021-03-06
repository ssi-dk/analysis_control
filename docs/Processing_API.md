# The Processing API

The Processing API only accepts one sequence per request, but does
accept multiple analysis tools per request.

Before running a sequence trough the Processing API, sequence data for
the sample must already exist in a folder on the filesystem. This folder
would normally (but will not necessarily) be an input folder from a
previous automatic run. There must also be a sample document in the
samples collection in the Bifrost database referring to that sample.

When running something through the Processing API, a new output folder
will always be created on the filesystem (even in the case of
reprocessing), and a new run document is added to the Bifrost database
in the runs collection. The actual results from the data processing are
added to the sample document in the Bifrost database, overwriting data
from a previous run, if any. On the filesystem, data is never
overwritten since we always use a new output folder for each run.

Typical use cases for the Processing API:

1.  A component that makes use of an external genetical database has
    been updated with a newer version of that database (resfinder, mlst,
    virulencefinder, and plasmidfinder all have genetical databases
    associated with them), and there's a need to reprocess samples with
    the new genetical database.
2.  A new version of a Bifrost component has been installed, and there
    is a need to reprocess samples with the new version. The Bifrost
    cronjobs will *not* automatically reprocess samples in case of a new
    component version.

Use cases NOT handled by the Processing API:

-   The Bifrost pipeline unexpectedly stops before completion. The
    reason for this to happen could either be be code that meets a
    situation that it's not designed to handle, or a problem at a deeper
    technical level (network, disk space, memory etc.). This is an error
    situation and not a situation that should be handled by end users
    but by sysadmins, and thus not a situation that we should need an
    API for either. Note: this is actually the use case that the Run
    Checker deals with, which means the the Processing API is NOT a
    replacement for the Run Checker. Run Checker does not make new run,
    but only aims to 'repair' a run that has failed.
-   An *entirely* new component is installed into the Bifrost pipeline
    system. In this case, the new component should be added to the cron
    jobs, meaning that it *will* run the new component with all relevant
    samples (and this will probably take some time).

## 
