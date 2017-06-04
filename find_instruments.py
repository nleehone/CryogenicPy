import pyvisa
import itertools
import visa
import tkinter as tk
from tkinter import ttk, messagebox

import importlib
mock = importlib.import_module("pyvisa-mock")


# Standard baud rates
BAUD_RATES = [110,
300,
600,
1200,
2400,
4800,
9600,
14400,
19200,
28800,
38400,
56000,
57600,
115200,
]

"""Non-standard baud-rates can be added:
[
128000,
153600,
230400,
256000,
460800,
921600,
]
"""

DATA_BITS = [5, 6, 7, 8]
PARITY = ["None", "Odd", "Even", "Mark", "Space"]
STOP_BITS = ["1", "1.5", "2"]
TERMINATION_CHAR = ["\\n", "\\r"]


class ConnectionParams:
    def __init__(self):
        self.baud_rate = None
        self.parity = None
        self.data_bits = None
        self.termination_char = None
        self.stop_bits = None
        self.timeout = None

    def __repr__(self):
        return "{{'baud_rate': {}, " \
               "'parity': {}, " \
               "'data_bits': {}, " \
               "'stop_bits': {}, " \
               "'timeout': {}, " \
               "'termination_char': {}}}".format(self.baud_rate,
                                               self.parity,
                                               self.data_bits,
                                               self.stop_bits,
                                               self.timeout,
                                               self.termination_char)


class InstrumentFinder(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.resource_manager = pyvisa.ResourceManager('instruments.yaml@mock')
        self.instrument_list = []
        self.parity = tk.StringVar()
        self.data_bits = tk.StringVar()
        self.baud_rate = tk.StringVar()
        self.stop_bits = tk.StringVar()
        self.termination = tk.StringVar()
        self.query = tk.StringVar()
        self.query.set("*IDN?")
        self.timeout = tk.DoubleVar()
        self.timeout.set(0.5)

        self.init_ui()

    def create_left_pane(self, paned_window):
        f1 = tk.Frame(paned_window)

        tk.Label(f1, text="Instruments", justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X)
        tk.Button(f1, text="Refresh", command=self.on_refresh_instruments).pack(side=tk.BOTTOM)

        scrollbar = tk.Scrollbar(f1)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.instrument_listbox = tk.Listbox(f1)
        self.instrument_listbox.bind("<<ListboxSelect>>", self.on_select_instrument)
        self.instrument_listbox.pack(fill=tk.BOTH, expand=1)
        self.instrument_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.instrument_listbox.yview)

        paned_window.add(f1)

    def create_center_pane(self, paned_window):
        f2 = tk.Frame(paned_window)

        tk.Label(f2, text="Instrument:", justify=tk.LEFT, anchor=tk.W).grid(row=0, column=0, columnspan=2)
        self.selected_instrument = tk.StringVar()
        self.selected_instrument_label = tk.Label(f2, text=0, textvariable=self.selected_instrument, justify=tk.LEFT,
                                                  anchor=tk.W)
        self.selected_instrument_label.grid(row=1, column=0, columnspan=2)
        row = 2

        row = self.create_label_combobox(f2, "Baud rate:", self.baud_rate, BAUD_RATES, row, 6)
        row = self.create_label_combobox(f2, "Data bits:", self.data_bits, DATA_BITS, row, 3)
        row = self.create_label_combobox(f2, "Parity:", self.parity, PARITY, row, 0)
        row = self.create_label_combobox(f2, "Stop bits:", self.stop_bits, STOP_BITS, row, 0)
        row = self.create_label_combobox(f2, "Termination char:", self.termination, TERMINATION_CHAR, row, 0)
        label = tk.Label(f2, text='Timeout:')
        entry = ttk.Entry(f2, textvariable=self.timeout)
        self.add_row(row, label, entry)
        row += 1
        label = tk.Label(f2, text='Query:')
        entry = ttk.Entry(f2, textvariable=self.query)
        self.add_row(row, label, entry)
        row += 1

        tk.Button(f2, text="Connect", command=self.on_connect).grid(row=row, column=0)
        tk.Button(f2, text="Find connection params", command=self.on_find_connection_params).grid(row=row, column=1)

        paned_window.add(f2)

    def create_label_combobox(self, parent, text, textvariable, data, row, current=0):
        label = tk.Label(parent, text=text)
        combobox = ttk.Combobox(parent, textvariable=textvariable)
        combobox['values'] = data
        combobox.current(current)
        self.add_row(row, label, combobox)
        return row + 1

    def create_right_pane(self, paned_window):
        f3 = tk.Frame(paned_window)

        scrollbar = tk.Scrollbar(f3, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_box = tk.Text(f3, wrap=tk.WORD)
        self.status_box.pack(fill=tk.BOTH, expand=1)
        self.status_box.config(yscrollcommand=scrollbar.set)
        self.status_box.config(state=tk.DISABLED)
        scrollbar.config(command=self.status_box.yview)

        button = tk.Button(f3, text="Clear Messages", command=self.on_clear_messages)
        button.pack()

        paned_window.add(f3)

    def init_ui(self):
        self.parent.title("Instrument Finder")
        self.pack(fill=tk.BOTH, expand=1)

        w = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        w.pack(fill=tk.BOTH, expand=1)

        self.create_left_pane(w)
        self.create_center_pane(w)
        self.create_right_pane(w)

        self.on_refresh_instruments()

    def add_row(self, row, el1, el2):
        el1.grid(row=row, column=0, sticky=tk.W)
        el2.grid(row=row, column=1)

    def connect(self, resource, query, connection_params):
        resource.timeout = connection_params.timeout * 1000 # Convert from s to ms
        resource.baud_rate = int(connection_params.baud_rate)
        resource.data_bits = int(connection_params.data_bits)
        resource.parity = {"Odd": visa.constants.Parity.odd,
                           "Even": visa.constants.Parity.even,
                           "None": visa.constants.Parity.none,
                           "Space": visa.constants.Parity.space,
                           "Mark": visa.constants.Parity.mark}[connection_params.parity]
        resource.stop_bits = {"1": visa.constants.StopBits.one,
                              "1.5": visa.constants.StopBits.one_and_a_half,
                              "2": visa.constants.StopBits.two}[connection_params.stop_bits]
        resource.termination = connection_params.termination_char
        return resource.query(query)

    def on_connect(self):
        try:
            instrument = self.selected_instrument.get()
            resource = self.resource_manager.open_resource(instrument)
            self.append_to_status_box("Attempting to connect to instrument: {}".format(instrument))
            connection_params = ConnectionParams()
            connection_params.termination_char = self.termination.get()
            connection_params.stop_bits = self.stop_bits.get()
            connection_params.parity = self.parity.get()
            connection_params.data_bits = self.data_bits.get()
            connection_params.baud_rate = self.baud_rate.get()
            connection_params.timeout = self.timeout.get()
            result = self.connect(resource, self.query.get(), connection_params)
            self.append_to_status_box("Got response: {}".format(result))
        except visa.VisaIOError as e:
            self.append_to_status_box("Error connecting: {}".format(e))
        except tk.TclError as e:
            messagebox.showinfo("Error", "{}".format(e))
            self.append_to_status_box("An error occurred while trying to connect.")
        except AttributeError as e:
            messagebox.showinfo("Error", "Please select an instrument")
            self.append_to_status_box("An error occurred while trying to connect.")
        except Exception as e:
            self.append_to_status_box("{}".format(e))

        self.append_to_status_box("------------------\n")

    def on_find_connection_params(self):
        try:
            instrument = self.selected_instrument.get()
            resource = self.resource_manager.open_resource(instrument)
            self.append_to_status_box("Attempting to find connection parameters for instrument: {}".format(instrument))
            good_connection_params = self.find_connection_params(resource)
            self.append_to_status_box("Found the following sets of connection parameters: {}".format(good_connection_params))
        except visa.VisaIOError as e:
            self.append_to_status_box("Error connecting: {}".format(e))
        except tk.TclError as e:
            messagebox.showinfo("Error", "{}".format(e))
            self.append_to_status_box("An error occurred while trying to connect.")
        except AttributeError:
            messagebox.showinfo("Error", "Please select an instrument")
            self.append_to_status_box("An error occurred while trying to connect.")
        except Exception as e:
            self.append_to_status_box("{}".format(e))

        self.append_to_status_box("------------------\n")

    def find_connection_params(self, resource):
        good_connection_params = []
        connection_params = ConnectionParams()
        connection_params.timeout = self.timeout.get()


        for stop_bits, parity, baud_rate, data_bits, termination in itertools.product(STOP_BITS, PARITY, BAUD_RATES,
                                                                                      DATA_BITS, TERMINATION_CHAR):
            try:
                connection_params.data_bits = data_bits
                connection_params.parity = parity
                connection_params.stop_bits = stop_bits
                connection_params.termination_char = termination
                connection_params.baud_rate = baud_rate

                self.append_to_status_box("Trying: {}".format(connection_params))
                result = self.connect(resource, self.query.get(), connection_params)
                self.append_to_status_box("Got response: {}".format(result))
                good_connection_params.append(connection_params)
            except visa.VisaIOError as e:
                self.append_to_status_box("Error connecting: {}\n".format(e))
        return good_connection_params

    def on_clear_messages(self):
        self.status_box.config(state=tk.NORMAL)
        self.status_box.delete(1.0, tk.END)
        self.status_box.config(state=tk.DISABLED)
        self.status_box.see(tk.END)

    def on_refresh_instruments(self):
        self.instrument_list = self.resource_manager.list_resources()
        self.instrument_listbox.delete(0, tk.END)
        for instrument in self.instrument_list:
            self.instrument_listbox.insert(tk.END, instrument)

    def on_select_instrument(self, val):
        sender = val.widget
        idx = sender.curselection()
        value = sender.get(idx)

        self.selected_instrument.set(value)
        self.status_box.insert(tk.END, value)

    def append_to_status_box(self, text):
        self.status_box.config(state=tk.NORMAL)
        self.status_box.insert(tk.END, text + "\n")
        self.status_box.config(state=tk.DISABLED)
        self.status_box.see(tk.END)


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("1024x800")
    app = InstrumentFinder(root)
    root.mainloop()