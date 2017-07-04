from myhdlpeek import *

trc1 = Trace([Sample(0,0), Sample(10,5), Sample(20,3), Sample(30,0)])

traces_to_text_table(trc1)
traces_to_text_table(trc1.delay(1).binarize() ^ trc1.binarize())
traces_to_text_table(trc1.anyedge())
print(trc1.anyedge().trig_times())
traces_to_text_table(trc1>3)
traces_to_text_table(trc1.anyedge() & (trc1>3))
