import tkinter as tk
import json
import subprocess


instruments = [
    {
        'name': 'LS350',
        'baud_rate': 57600,
        'data_bits': 7,
        'parity': 'odd',
        'driver': 'LS350Driver.py',
        'address': 'ASRL9::INSTR',
    },
    {
        'name': 'SR830',
        'baud_rate': 19200,
        'data_bits': 8,
        'parity': 'none',
        'stop_bits': 'one',
        'termination': 'CR',
        'driver': 'SR830Driver.py',
        'address': 'ASRL4::INSTR'
    }
]


class DriverManager(tk.Frame):
    subprocesses = {}

    def __init__(self, instruments, master=None):
        super().__init__(master)
        self.pack()
        self.status = {}

        for i, instrument in enumerate(instruments):
            self.add_instrument(i, instrument)

        self.check_status()

    def add_instrument(self, row, instrument):
        label = tk.Label(self, text=instrument['name'])
        label.grid(row=row, column=0)

        label = tk.Label(self, text='    ', bg='red')
        label.grid(row=row, column=1, padx=10)
        self.status[row] = label

        def spawn_proc(params):
            self.subprocesses[row] = subprocess.Popen(['python', instrument['driver'], json.dumps(params)])

        button = tk.Button(self, text='Start', command=lambda: spawn_proc(instrument))
        button.grid(row=row, column=2)

        button = tk.Button(self, text='Stop', command=lambda: self.subprocesses[row].terminate())
        button.grid(row=row, column=3)

    def check_status(self):
        for key, proc in self.subprocesses.items():
            if proc.poll() is None:
                self.status[key].configure(background='green')
            else:
                self.status[key].configure(background='red')

        root.after(100, self.check_status)


if __name__ == '__main__':
    root = tk.Tk()
    dm = DriverManager(instruments, root)
    root.mainloop()
