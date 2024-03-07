# Decision Server with OpenAI Gym and gRPC

This project contains a custom implementation of an OpenAI Gym environment that communicates with a gRPC server to make decisions. The environment is defined in the CustomGymEnv class in the decision_server.py file.

On the other hand, the observation_client.py file contains a client that connects to the gRPC server and sends observations to it on an infinite loop.

## Overview

The CustomGymEnv class is a custom Gym environment that uses two queues to communicate with a gRPC server. The action_queue is used to send actions from the environment to the server, and the observation_queue is used to receive observations from the server to the environment.

## The Environment

The agent starts at (0,0) and must reach state (3,3) where the observation's state is set to 1. The agent can move up, down, left, or right, or stay still. The gym environment is defined in the CustomGymEnv class in the decision_server.py file. The agent can also send a special action to reset the environment to its initial state.

## How it works

When an action is taken in the environment (via the step method), the action is put into the action_queue. The DecisionServicer then gets the action from the queue, processes it, and puts the resulting observation into the observation_queue. The environment then gets the observation from the queue and returns it from the step method.

The reset method is used to reset the environment to its initial state. It also puts a special reset action (-1) into the action_queue.

The observation_class_to_ndarray method is used to convert the observation from the gRPC message class to a numpy array.
