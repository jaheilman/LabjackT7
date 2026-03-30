from labjack import ljm
# from .core import LabjackT7
# from scipy.signal import resample
import numpy as np
from datetime import datetime

class StreamConfig():
    def __init__(self, settling_time=0, resolution_index=0, clock_source=0):
        self.stream_config_dict = {
            'STREAM_SETTLING_US': settling_time,
            'STREAM_RESOLUTION_INDEX': resolution_index,
            'STREAM_CLOCK_SOURCE': clock_source,
        }
                    
class Stream():
    def __init__(self, labjack):
        self.labjack = labjack
        self.configure()

    def configure(self, settling_time=0, resolution_index=0, clock_source=0):
        self.stop()
        self.labjack._write_dict({
            'STREAM_SETTLING_US': settling_time,
            'STREAM_RESOLUTION_INDEX': resolution_index,
            'STREAM_CLOCK_SOURCE': clock_source
        })
        #STREAM_TRIGGER_INDEX

    def configure_from_dict(self, stream_options: dict):
        self.labjack._write_dict(stream_options)

    def set_inhibit(self, channels):
        bitmask = self.labjack.digital.bitmask(channels)
        inhibit = 0x7FFFFF-bitmask

        self.labjack._write_dict({'DIO_INHIBIT': inhibit,
                                  'DIO_DIRECTION': bitmask
                                  })

    def stop(self):
        ''' Stop streaming if currently running '''
        try:
            ljm.eStreamStop(self.labjack.handle)
        except:
            pass

    #disabled because removed scipy.signal.resample()
    # def resample(self, array, period, max_samples = 8191):
    #     ''' Compute optimum scan rate and number of samples '''
    #     max_speed = self._device_scanRate()
    #     cutoff = max_samples / max_speed
    #     if period >= cutoff:
    #         samples = max_samples
    #         scanRate = int(samples/period)
    #     else:
    #         scanRate = max_speed
    #         samples = int(period*scanRate)
    #     # stream = resample(array, samples)
    #     stream = []
    #     scanRate /= array.shape[1]    ## divide by number of channels being streamed
    #     return stream, scanRate

    def stream_burst(self, aScanListNames:list, scanRate:int=0, scanTime_s:float=1) -> list:
        ''' 
            Args:
                scanListNames: ["AIN0", "AIN1"] etc
                scan_rate: 0 for max rate
                scan_time_s: number of seconds to sample (default 1)
        '''
        aScanList = ljm.namesToAddresses(len(aScanListNames), aScanListNames)[0]  # Names to addresses for streamBurst
        if (scanRate <= 0) or (scanRate > self._device_scanRate()):
            scanRate = self._device_scanRate()
        num_scans = int(scanTime_s*scanRate)  # Number of scans to perform
        num_scans = num_scans - (num_scans % len(aScanList)) # ensure all channels have equal samples
        start = datetime.now()
        scanRate, aData = ljm.streamBurst(self.labjack.handle, len(aScanList), aScanList, scanRate, num_scans)
        end = datetime.now()
        if False:
            print(f"Channels: {len(aScanListNames)},  Samples per Ch: {len(aData)/len(aScanListNames)}, ScanRate: {scanRate}, Elapsed Time = {(end - start).seconds + float((end - start).microseconds) / 1000000}s" )
        if aData.count(-9999.0) > 0:
            print(f"WARNING: some samples were skipped! Total skips, all channels) = f{aData.count(-9999.0)}")
        return scanRate, self._reshape_data(aData, len(aScanList))

    def stream_start(self, channels:list, scan_rate):
        self.stop()
        scan_list = ljm.namesToAddresses(len(channels), channels)[0]

        scans_per_read = int(scan_rate/2)
        ljm.eStreamStart(self.labjack.handle, scans_per_read, len(channels), scan_list, scan_rate)

    def stream_read(self):
        return ljm.eStreamRead(self.labjack.handle)

    def aout(self, channels, data, scanRate, loop=0):
        self._start([1000+2*ch for ch in channels], data, scanRate, loop=loop, dtype='F32')

    def dout(self, data, scanRate, loop=0):
        self._start([2500], data, scanRate, loop=loop, dtype='U16')

    def _start(self, channels, data, scanRate, loop = 0, dtype='F32'):
        self.stop()
        n = np.ceil(np.log10(2*(1+len(data)))/np.log10(2))
        buffer_size = 2**n
        i = 0
        scan_list = []
        for ch in channels:
            self.labjack._write_dict({
                f'STREAM_OUT{i}_TARGET': ch,
                f'STREAM_OUT{i}_BUFFER_SIZE': buffer_size,
                f'STREAM_OUT{i}_ENABLE': 1
            })

            target = ['STREAM_OUT%i_BUFFER_%s'%(i, dtype)] * len(data)
            self.labjack._write_array(target, list(data[:, i]))

            self.labjack._write_dict({
                f'STREAM_OUT{i}_LOOP_SIZE': loop*len(data),
                f'STREAM_OUT{i}_SET_LOOP': 1
            })
            scan_list.append(4800+i)
            i += 1
        scanRate = ljm.eStreamStart(self.labjack.handle, 1, len(scan_list), scan_list, scanRate)

    def set_trigger(self, ch):
        if ch is None:
            self.labjack._command("STREAM_TRIGGER_INDEX", 0) # disable triggered stream
        else:
            self.labjack._write_dict({f"DIO{ch}_EF_ENABLE": 0
                              })
            self.labjack._write_dict({
                f"DIO{ch}_EF_INDEX": 3,
                f"DIO{ch}_EF_OPTIONS": 12,   ## current value: 0 (PWM Out)
                # f"DIO{ch}_EF_VALUE_A": 2,
                f"DIO{ch}_EF_CONFIG_A": 1,
                f"DIO{ch}_EF_CONFIG_B": 1,
                f"DIO{ch}_EF_ENABLE": 1,
                "STREAM_TRIGGER_INDEX": 2000+ch
                })
            ljm.writeLibraryConfigS('LJM_STREAM_RECEIVE_TIMEOUT_MS',0)  #disable timeout

    def _device_scanRate(self):
        if self.labjack.device_type == ljm.constants.dtT7:
            return 100000
        elif self.labjack.device_type == ljm.constants.dtT4:
            return 40000

    def _reshape_data(self, aData:list, num_channels:int):
        ''' splits scan data into list of lists'''
        channels = []
        ch = []
        for i in range(num_channels):
            ch = aData[i:][::num_channels]
            channels.append(ch)
        return channels