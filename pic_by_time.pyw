""" Order pictures from different cameras.
Normally file's modified date time reflect their actual shooting time.

Note: If a photo is touched-up, then the attribure is changing and this approach does not work nicely.
Potential solution is https://stackoverflow.com/questions/12521525/reading-metadata-with-python
win32com did not seem to be picked up by pip, hence sticking to the naive solution

Developed and tested on Win10, Python 3.10 with tcl/tk
"""
import os
import shutil
import datetime
import tkinter as tk
import tkinter.ttk as ttk

src_f_path = "C:/"

def order_copy(src_f_path, tgt_f_path, app=None):
    try:
        src_dir_list = os.listdir(src_f_path)
    except FileNotFoundError as e:
        return "[ERROR] " + repr(e)

    src_f_path_names = [os.path.join(src_f_path, f) for f in src_dir_list if os.path.isfile(os.path.join(src_f_path, f))]

    shutil.rmtree(tgt_f_path, ignore_errors=True)
    os.makedirs(tgt_f_path, exist_ok=True)

    for f_path_name in src_f_path_names:
        mtime_epoch = os.path.getmtime(f_path_name)
        mtime_dts = datetime.datetime.fromtimestamp(mtime_epoch)
        f_name = os.path.basename(f_path_name)
        f_prefix = mtime_dts.strftime('%Y%m%dT%H%M%S')
        tgt_f_name = f_prefix + "-" + f_name
        tgt_f_path_name = os.path.join(tgt_f_path, tgt_f_name)
        shutil.copy2(f_path_name, tgt_f_path_name)
            
    return f"Done. {tgt_f_path}"


class App(tk.Frame):
    def __init__(self, master):
        global src_f_path

        super().__init__(master)
        self.master.title("Order by Time")
        self.master.geometry('550x100')

        self.src_lbl = ttk.Label(text="Source Dir")
        self.src_lbl.grid(column=0, row=0)
        self.src_fld = ttk.Entry(width=80, textvariable=src_f_path)
        self.src_fld.insert(0, src_f_path)
        self.src_fld.grid(column=1, row=0, padx=2, pady=2)

        self.tgt_lbl = ttk.Label(text="Target Dir")
        self.tgt_lbl.grid(column=0, row=1)
        tgt_f_path = os.path.join(src_f_path, "out")
        self.tgt_fld = ttk.Entry(width=80, textvariable=tgt_f_path)
        self.tgt_fld.insert(0, tgt_f_path)
        self.tgt_fld.grid(column=1, row=1, padx=2, pady=2)

        self.btn = tk.Button(text="Go!", command=self.go_btn_clicked)
        self.btn.grid(column=0, row=2, columnspan=2, padx=2, pady=3)

        self.status_lbl = ttk.Label(text="Click [Go!]")
        self.status_lbl.grid(column=0, row=3, columnspan=2, padx=2, pady=2)

    def go_btn_clicked(self):
        status = order_copy(self.src_fld.get(), self.tgt_fld.get(), app=self)
        self.status_lbl.configure(text=status)


def main():
    global src_f_path

    root = tk.Tk()
    app = App(root)
    app.mainloop()
    
if __name__ == "__main__":
    main()
