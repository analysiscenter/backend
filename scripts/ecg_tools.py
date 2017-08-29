import datetime
import numpy as np


def ecg_signal(pid):
    signal = np.round(np.sin(np.linspace(0, 10*np.pi, 1000)), 4)
    fs = 300
    name = "Patient_" + str(pid)
    age = np.random.randint(low=0, high=100)
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    units = "mV"
    lead = "I"
    output = {'signal': signal.tolist(),
              'id' : pid,
              'frequency': fs,
              'name': name,
              'age': age,
              'date': date,
              'units': units,
              'lead': lead
             }
    return output

def analysis_results(pid):
    qrs = np.arange(0, 1000, 10)
    af_prob = float(format(np.random.rand(), '.2f'))
    heart_rate = np.random.randint(low=60, high=120)
    data = {'qrs_peaks': qrs.tolist(),
            'af_prob': af_prob,
            'heart_rate': heart_rate
           }
    return data
