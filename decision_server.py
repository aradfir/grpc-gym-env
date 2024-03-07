
import time
import grpc
from concurrent import futures

import numpy as np
import observation_decision_pb2
import observation_decision_pb2_grpc
import gymnasium as gym
import threading
import queue
from stable_baselines3 import PPO,A2C,TD3
from stable_baselines3.common.env_checker import check_env

class CustomGymEnv(gym.Env):
    
    def __init__(self):
        super(CustomGymEnv, self).__init__()
        # create observation space of the environment, ndarray of 2
        self.observation_space = gym.spaces.Box(low=-10, high=10, shape=(2,), dtype=np.float32)
        # self.observation_space = gym.spaces.Tuple((gym.spaces.Discrete(5), gym.spaces.Discrete(5)))
        
        self.action_queue = queue.Queue(1)
        self.observation_queue = queue.Queue(1)
        self.episode_reward = 0
        self.old_observation = None
        self.action_space = gym.spaces.Discrete(5)
    
    def wait_for_observation_and_return(self):
        observation = self.observation_queue.get(block=True)
        return self.observation_class_to_ndarray(observation), {}
    
    def reset(self, seed = -1):
        # set selected action as -1, the special reset action
        print(f"Reseting! Episode Reward:{self.episode_reward}")
        self.episode_reward = 0
        self.do_action(-1, True)
        return self.wait_for_observation_and_return()
    
    def clear_actions_queue(self):
        with self.action_queue.mutex:
            self.action_queue.queue.clear()

    def clear_observation_queue(self):
        with self.observation_queue.mutex:
            self.observation_queue.queue.clear()

    def observation_class_to_ndarray(self, observation):
        return np.array([observation.x, observation.y])
    
    def do_action(self, action, clear_actions: bool = False):
        if clear_actions:
            self.clear_actions_queue()
        self.action_queue.put(action,block=False)
        
    def get_best_action(self, observation):
        if observation[0] < 2:
            return 0
        elif observation[0] > 2:
            return 2
        if observation[1] < 2:
            return 1
        elif observation[1] > 2:
            return 3
        return 4
    
    def step(self, action):
        # set selected action as the action chosen by the decision server
        self.clear_observation_queue()
        self.do_action(action)
        observation = self.observation_queue.get(block = True)
       
        # now latest observation is loaded from DecisionServicer
        
        converted_observation = self.observation_class_to_ndarray(observation)
        if self.old_observation is None:
            self.old_observation = converted_observation
        if observation.state == 1:
            reward = 1000
            done = True
        elif abs(observation.x) > 10 or abs(observation.y) > 10:
            reward = -1000
            done = True
        else:
            done = False
            # get how much closer we have gotten to goal [3,3] since last step
            manhattan_dist_to_goal = abs(observation.x - 3) + abs(observation.y - 3) - abs(self.old_observation[0] - 3) - abs(self.old_observation[1] - 3)
            reward = -0.5 * manhattan_dist_to_goal
            # set this as the reward to simulate a sparsely rewarded world
            # reward = -1
        self.episode_reward += reward
        self.old_observation = converted_observation
        return converted_observation, reward, done, False, {}
    
class DecisionServicer(observation_decision_pb2_grpc.DecisionServicer):
    def __init__(self,env):
        super(DecisionServicer, self).__init__()
        self.gym_env: CustomGymEnv = env
    def GetAction(self, request, context):
        # print(f"Received Observation: {request}")
        self.gym_env.clear_actions_queue()
        self.gym_env.observation_queue.put(request, block=False)
        selected_action = self.gym_env.action_queue.get(block = True)           
        action = observation_decision_pb2.Action(action= selected_action)
        # print(f"Sending Action: {action}")
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
    # check_env(env)
    
    model = A2C("MlpPolicy", env)
    model.learn(total_timesteps=10_000, progress_bar=True)
    # model.load("a2c_custom_gym")
    print("Training done")
    model.save("a2c_custom_gym")
    input("Press Enter to continue...")
    # observation, info = env.reset()
    observation, _ = env.reset()
    while server_thread.is_alive():
        # sample action from the environment
        action = model.predict(observation)[0]
        print(f"Action: {action}")
        # get observation from the environment
        observation, reward, done,truncated, info = env.step(action)
        print(f"Observation: {observation}, Reward: {reward}, Done: {done}, Info: {info}")
        if done:
            observation, info = env.reset()
            print("Environment reset")
        else:
            print("Environment not reset")