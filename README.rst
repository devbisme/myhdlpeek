===============================
myhdlpeek
===============================

.. image:: https://img.shields.io/pypi/v/myhdlpeek.svg
        :target: https://pypi.python.org/pypi/myhdlpeek


A module that lets you monitor signals in a 
`MyHDL <http://www.myhdl.org/>`_ or `Amaranth <https://github.com/amaranth-lang>`_
digital system simulation and display them as waveforms in a Jupyter notebook.
Make changes to your digital design and see the results reflected immediately in the
waveforms of your notebook!

`myhdlpeek` implements a `Peeker` object that monitors a signal and records
the time and value when it changes.
Just add multiple Peekers where you want to monitor something (even at sub-levels
of a hierarchical design) and then view the collected timing waveforms
with a single command.
You can also select which signals are shown, set the beginning and
ending times of the display, and much more.

`[This Jupyter notebook] <https://github.com/devbisme/myhdlpeek/blob/master/examples/complete.ipynb>`_ 
shows how to use myhdlpeek.

|

* Free software: MIT license
* Documentation: http://devbisme.github.io/myhdlpeek

Features
--------

* Captures timing traces of signals in a MyHDL/Amaranth digital design.
* Works at the top-level and sub-levels of a hierarchical design.
* All signals or a selected subset can be displayed.
* The beginning and ending points of the waveform display can be set.
* Timing marks can be turned on or off.
* Titles and captions are supported.
* Tabular output in Jupyter and console.
* Trigger expressions allow the display of a selected portion of traces.
