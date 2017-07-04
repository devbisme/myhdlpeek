from myhdl import Signal, Simulation, delay, always_comb, intbv, now, instances
from myhdlpeek import Peeker, show_text_table


def Mux(z, a, b, sel):
    """ Multiplexer.

    z -- mux output
    a, b -- data inputs
    sel -- control input: select a if asserted, otherwise b

    """

    @always_comb
    def muxLogic():
        if sel == 1:
            z.next = a
        else:
            z.next = b

    Peeker(z, 'r')
    Peeker(a, 'a')
    Peeker(b, 'b')
    Peeker(sel, 'sel')

    return muxLogic


# Once we've created some signals...
z, a, b, z2 = [Signal(intbv(0, min=0, max=8)) for i in range(4)]
sel = Signal(bool(0))

Peeker.clear()

# ...it can be instantiated as follows
mux_1 = Mux(z, a, b, sel)
mux_2 = Mux(z2, b, a, sel)

from random import randrange


def test():
    for i in range(8):
        a.next, b.next, sel.next = randrange(8), randrange(8), randrange(2)
        yield delay(2)


test_1 = test()
sim = Simulation(mux_1, mux_2, test_1, *Peeker.instances()).run()
# for p in Peeker.peekers():
# print(p.trace)
#print(Peeker.to_json('sel[0]', 'a[0]', 'b[0]', 'z[0]', start_time=3, stop_time=7))
show_text_table()
#print(Peeker.to_json())
