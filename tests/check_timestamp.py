from datetime import datetime, timedelta

num = 1903590565

results = []

results.append('=== Interpreting 1903590565 as various timestamp formats ===')

try:
    dt = datetime.fromtimestamp(num)
    results.append(f'Unix seconds (local):       {dt}')
except Exception as e:
    results.append(f'Unix seconds: out of range ({e})')

apple_epoch = datetime(2001, 1, 1)
dt = apple_epoch + timedelta(seconds=num)
results.append(f'Apple CFAbsoluteTime:       {dt}')

dt = datetime.fromtimestamp(num / 1000)
results.append(f'Unix milliseconds (local):  {dt}')

dt = apple_epoch + timedelta(seconds=num / 1_000_000_000)
results.append(f'Apple nanoseconds:          {dt}')

with open('ts_result.txt', 'w') as f:
    f.write('\n'.join(results))

