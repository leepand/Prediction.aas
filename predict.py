# fib.py

def predict(n):
	if n == 0 or n == 1:
		return 1
	else:
		return predict(n-1) + predict(n-2)
