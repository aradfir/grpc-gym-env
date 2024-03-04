import random
import time
import grpc
from concurrent import futures
import observation_decision_pb2
import observation_decision_pb2_grpc
import gymnasium as gym
import threading
import queue

class CustomGymEnv(gym.Env):
    
    def __init__(self):
        super(CustomGymEnv, self).__init__()
        self.observation_space = gym.spaces.Tuple((gym.spaces.Discrete(5), gym.spaces.Discrete(5)))
        
        self.action_queue = queue.Queue(1)
        self.observation_queue = queue.Queue(1)
        self.wants_reset = False
        self.episode_reward = 0
        self.action_space = gym.spaces.Discrete(5)
    
    def wait_for_observation_and_return(self):
        observation = self.observation_queue.get(block=True)
        return observation
    def reset(self):
        # set selected action as -1, the special reset action
        print(f"Reseting! Episode Reward:{self.episode_reward}")
        self.episode_reward = 0
        self.wants_reset = True
        
    def get_best_action(self, observation):
        if observation.x < 2:
            return 0
        elif observation.x > 2:
            return 2
        if observation.y < 2:
            return 1
        elif observation.y > 2:
            return 3
        return 4
    def step(self, action):
        # set selected action as the action chosen by the decision server
        with self.observation_queue.mutex:
            self.observation_queue.queue.clear()
        self.action_queue.put(action,block=False)
        observation = self.observation_queue.get(block = True)
        
        # now latest observation is loaded from DecisionServicer
        if observation.state == 1:
            return observation, 1000, True, {}
        if abs(observation.x) > 10 or abs(observation.x) > 10:
            return observation, -1000, True, {}
        
        manhattan_dist_to_goal = abs(observation.x - 2) + abs(observation.y - 2)
        reward = -0.5 * manhattan_dist_to_goal
        return observation, reward, False, {}
    
class DecisionServicer(observation_decision_pb2_grpc.DecisionServicer):
    def __init__(self,env):
        super(DecisionServicer, self).__init__()
        self.gym_env: CustomGymEnv = env
    # def GetAction(self, request, context):
    #     # return random response
    #     action = observation_decision_pb2.Action(action = random.choice([0,1,2,3,4]))
    #     return action
    def GetAction(self, request, context):
        print(f"Received Observation: {request}")
        with self.gym_env.action_queue.mutex:
            self.gym_env.action_queue.queue.clear()
        if self.gym_env.wants_reset:
            print("Wants to reset! sending reset action!")
            action = observation_decision_pb2.Action(action=-1)
            self.gym_env.wants_reset = False
            return action
        self.gym_env.observation_queue.put(request, block=False)
        selected_action = self.gym_env.action_queue.get(block = True)
        action = observation_decision_pb2.Action(action= selected_action)
        print(f"Sending Action: {action}")
        return action


def serve(gym_env):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    observation_decision_pb2_grpc.add_DecisionServicer_to_server(DecisionServicer(gym_env), server)
    server.add_insecure_port('localhost:5005')
    server.start()
    print("Decision Server started. Listening on port 5005...")
    try:
        while True:
            time.sleep(60 * 60 * 24)  # Sleep for a day or any desired interval
    except KeyboardInterrupt:
        print("Shutting down the server...")
        server.stop(0)

if __name__ == '__main__':
    env = CustomGymEnv()
    # serve on different thread
    # serve(env)
    # Create a new thread for running the server
    server_thread = threading.Thread(target=serve, args=(env,))
    server_thread.start()
    observation = env.wait_for_observation_and_return()
    while server_thread.is_alive():
        # sample action from the environment
        action = env.get_best_action(observation)
        print(f"Action: {action}")
        # get observation from the environment
        observation, reward, done, info = env.step(action)
        env.episode_reward += reward
        print(f"Observation: {observation}, Reward: {reward}, Done: {done}, Info: {info}")
        if done:
            env.reset()
            print("Environment reset")
        else:
            print("Environment not reset")