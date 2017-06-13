import visa
import time

rm = visa.ResourceManager()
resource = rm.open_resource('ASRL9::INSTR')
resource.read_termination = '\x13'
resource.clear()
#print(resource.read())
t0 = time.time()
print(resource.query('GET PER'
                     ''
                     ''
                     ''
                     ''
                     ''
                     ''
                     ''
                     ''
                     ''))
#print(resource.read())
try:
    print(resource.read())
except Exception as e:
    print(e)
print(time.time() - t0)

#t0 = time.time()
#print(len(resource.query('TESLA')))
#print(len(resource.query('G O')))
#print(len(resource.query('G L')))
#print(time.time() - t0)