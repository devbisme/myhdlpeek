===============================
myhdlpeek
===============================

.. image:: https://img.shields.io/pypi/v/myhdlpeek.svg
        :target: https://pypi.python.org/pypi/myhdlpeek


A module that lets you monitor signals in a 
`MyHDL <http://myhdl.org>`_ digital system simulation
and display them as waveforms in a Jupyter notebook.
Make changes to your digital design and see the results reflected immediately in the
waveforms of your notebook!

`myhdlpeek` uses a `Peeker` objects that monitor signals and records
the time and value when they change.
Just add the Peekers where you want to monitor something (even at sub-levels
of a hierarchical design) and then view the collected timing waveforms
with a single command.
You can also select which signals are shown, set the beginning and
ending times of the display, and set other options.

Here are some examples of Jupyter notebooks using myhdlpeek:

* `Simple multiplexer.   <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_simple_mux.ipynb>`_
* `Hierarchical adder.   <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_hier_add.ipynb>`_
* `Other Peeker options. <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_options.ipynb>`_

|

* Free software: MIT license
* Documentation: http://xesscorp.github.io/myhdlpeek

Features
--------

* Captures timing traces of signals in a MyHDL digital design.
* Works at the top-level and sub-levels of a hierarchical design.
* All signals or a selected subset can be displayed.
* The beginning and ending points of the waveform display can be set.
* Timing marks can be turned on or off.
* Titles and captions are supported.
