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

`myhdlpeek` implements a `Peeker` object that monitors a signal and records
the time and value when it changes.
Just add multiple Peekers where you want to monitor something (even at sub-levels
of a hierarchical design) and then view the collected timing waveforms
with a single command.
You can also select which signals are shown, set the beginning and
ending times of the display, and set other options.

Below are some examples of Jupyter notebooks using myhdlpeek.
Unfortunately, the Github Notebook viewer doesn't render the waveform displays
so you'll have to download and run the notebooks locally or click on the static HTML
link to see what myhdlpeek can do.

* Simple multiplexer: `[Notebook1] <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_simple_mux.ipynb>`_ `[HTML1] <http://www.xess.com/static/media/pages/peeker_simple_mux.html>`_
* Hierarchical adder: `[Notebook2] <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_hier_add.ipynb>`_ `[HTML2] <http://www.xess.com/static/media/pages/peeker_hier_add.html>`_
* Other Peeker options: `[Notebook3] <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_options.ipynb>`_ `[HTML3] <http://www.xess.com/static/media/pages/peeker_options.html>`_
* Tabular display: `[Notebook4] <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_tables.ipynb>`_ `[HTML4] <http://www.xess.com/static/media/pages/peeker_tables.html>`_
* Convenience functions: `[Notebook5] <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_convenience_functions.ipynb>`_ `[HTML5] <http://www.xess.com/static/media/pages/peeker_convenience_functions.html>`_
* Trigger functions: `[Notebook6] <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_triggers.ipynb>`_ `[HTML6] <http://www.xess.com/static/media/pages/peeker_triggers.html>`_
* Peeker groups: `[Notebook] <https://github.com/xesscorp/myhdlpeek/blob/master/examples/peeker_groups.ipynb>`_ `[HTML7] <http://www.xess.com/static/media/pages/peeker_groups.html>`_

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
* Tabular output in Jupyter and console.
* Trigger expressions allow the display of a selected portion of traces.
