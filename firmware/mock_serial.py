"""Send simulated scale readings over Pico USB serial without an HX711."""

import math
import random
import time

TARGET_GRAMS = 642.7
started = time.ticks_ms()

print("# Smart Clip mock scale")
print("# simulated grams at 2 Hz")

while True:
    elapsed = time.ticks_diff(time.ticks_ms(), started) / 1000
    swing = 36 * math.exp(-elapsed / 2.2) * math.cos(elapsed * 5.2)
    noise = (random.random() - 0.5) * 0.35
    print("%.1f" % (TARGET_GRAMS + swing + noise))
    time.sleep_ms(500)
