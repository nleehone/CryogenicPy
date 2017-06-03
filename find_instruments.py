import pyvisa
import tkinter as tk

import importlib
mock = importlib.import_module("pyvisa-mock")


class InstrumentFinder(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.resource_manager = pyvisa.ResourceManager('instruments.yaml@mock')
        self.instrument_list = []
        self.init_ui()

    def init_ui(self):
        self.parent.title("Instrument Finder")
        self.pack(fill=tk.BOTH, expand=1)

        w = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        w.pack(fill=tk.BOTH, expand=1)

        left = tk.Frame(w)
        w.add(left)

        self.instrument_list = self.resource_manager.list_resources()

        self.instrument_listbox = tk.Listbox(left)
        for instrument in self.instrument_list:
            self.instrument_listbox.insert(tk.END, instrument)
        self.instrument_listbox.bind("<<ListboxSelect>>", self.on_select_instrument)
        #self.instrument_listbox.pack(pady=15)
        self.instrument_listbox.pack(fill=tk.BOTH, expand=1)

        right = tk.Frame(w)
        #right.pack()
        w.add(right)

        self.selected_instrument = tk.StringVar()
        self.selected_instrument_label = tk.Label(right, text=0, textvariable=self.selected_instrument)
        self.selected_instrument_label.pack()



    def on_select_instrument(self, val):
        sender = val.widget
        idx = sender.curselection()
        value = sender.get(idx)

        self.selected_instrument.set(value)


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("600x400")
    app = InstrumentFinder(root)
    root.mainloop()