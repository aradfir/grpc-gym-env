from time import sleep
import grpc
import observation_decision_pb2
import observation_decision_pb2_grpc
import random



def create_state(current_x, current_y):
    if current_x == 2 and current_y == 2:
        state = 1
    else:
        state = 0
    
    return observation_decision_pb2.Observation(x=current_x, y=current_y, state=state)

def observation_client():
    x=0
    y=0
    channel = grpc.insecure_channel('localhost:5005', options=(('grpc.enable_http_proxy', 0),))
    stub = observation_decision_pb2_grpc.DecisionStub(channel)
    while True:
        observation = create_state(x,y)
        print(f"Observation Sent:\n {observation}")

        action = stub.GetAction(observation)
        print(f"Received Action: {action.action}")
        if action.action == 0:
            x += 1
        elif action.action == 1:
            y += 1
        elif action.action == 2:
            x -=1
        elif action.action == 3:
            y -=1
        elif action.action == 4:
            # do nothing
            pass
        elif action.action == -1: 
            # special reset action
            x=y=0
        sleep(1)

if __name__ == '__main__':
    observation_client()