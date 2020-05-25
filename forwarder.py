import zmq

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL);

def main():

    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.SUB)
        frontend.bind("tcp://*:5559")
        frontend.setsockopt_string(zmq.SUBSCRIBE, "")


        # Socket facing services
        backend = context.socket(zmq.PUB)
        backend.bind("tcp://*:5560")
        print("Starting")
        zmq.device(zmq.FORWARDER, frontend, backend)

        print("Device set up")

    except Exception as e:
        print (e)
        print ("bringing down zmq device")
    finally:
        pass
        frontend.close()
        backend.close()
        context.term()

if __name__ == "__main__":
    main()
