.. :changelog:

History
-------


0.0.10 (2021-07-06)
______________________

* Moved ownership from xesscorp to devbisme (Dave Vandenbout).


0.0.9 (2021-01-05)
______________________

* Added support for nMigen.
* Waveforms can now be drawn using wavedrom or matplotlib.


0.0.8 (2018-09-25)
______________________

* Now works with the newer JupyterLab by default. Older Jupyter notebooks are still supported by setting ``myhdlpeek.USE_JUPYTERLAB = False``.
* Updated documentation.


0.0.7 (2018-04-13)
______________________

* Added functions to export signal traces into a Pandas dataframe.
* Updated documentation.


0.0.6 (2017-10-11)
______________________

* The skin can now be set for waveform traces (either 'default' or 'narrow').
* clear_traces() was added to remove signal trace data from Peekers without removing the Peekers so another simulation can be run.
* Updated documentation.
* Removed unused __main__.py.


0.0.5 (2017-08-25)
______________________

* Added PeekerGroup class to allow grouping of Peekers.
* Trace objects now only return integer values.


0.0.4 (2017-07-04)
______________________

* Added trigger capability to select a portion of traces for display.
* Extended waveform & table display to both Peekers and Traces.


0.0.3 (2017-06-23)
______________________

* Made compatible with Python 2.7.
* Added tabular output of Peeker data traces.


0.0.2 (2017-06-12)
______________________

* Added static HTML pages to display what myhdlpeek can do. (Notebook rendering with nbconvert won't show waveforms.)


0.0.1 (2017-06-10)
______________________

* First release on PyPI.
