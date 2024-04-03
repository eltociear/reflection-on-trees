import sys
import os

path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(1, path)

from typing import Type, Callable, Optional, Literal

from reasoners.benchmark import GSM8KEvaluator

from reasoners import Reasoner, SearchAlgorithm
from reasoners.algorithm import BFSNode, BFS
from reasoners import VLLMModel
from world_model import GSM8kWorldModel, GSM8kState, GSM8kAction, GSM8kPromptDict
from search_config import GSM8kConfig, GSM8kUsefulPrompt
import utils


def node_visualizer(x: BFSNode[GSM8kState, GSM8kAction]):
    if not x.state:
        return {}
    return {"question": x.state[-1].sub_question, "answer": x.state[-1].sub_answer}

def rap_gsm8k(base_model,
              prompt: GSM8kPromptDict,
              useful_prompt: GSM8kUsefulPrompt,
              search_algo: Type[SearchAlgorithm] = BFS,
              resume: int = 0,
              n_action: int = 4,
              n_confidence: int = 8,
              depth_limit: int = 5,
              force_terminating_on_depth_limit: bool = True,
              batch_size: int = 4,
              temperature: float = 0.8,
              early_stop_base: int = 2,
              early_stop_threshold: float = 0.5,
              reward_alpha: float = 0.5,
              reward_confidence_default: float = 0.8,
              log_dir: Optional[str] = None,
              disable_log: bool = False,
              disable_tqdm: bool = False,
              samples: int = -1,
              split: str = 'test',
              **search_algo_params):

    search_algo_params |= {'disable_tqdm': disable_tqdm,
                           'node_visualizer': node_visualizer}

    world_model = GSM8kWorldModel(base_model=base_model,
                                  n_confidence=n_confidence, batch_size=batch_size, temperature=temperature,
                                  early_stop_base=early_stop_base, early_stop_threshold=early_stop_threshold)
    config = GSM8kConfig(base_model=base_model, useful_prompt=useful_prompt,
                         n_actions=n_action, batch_size=batch_size, temperature=temperature,
                         reward_alpha=reward_alpha, reward_confidence_default=reward_confidence_default,
                         force_terminating_on_depth_limit=force_terminating_on_depth_limit, depth_limit=depth_limit)

    search_algo = search_algo(**search_algo_params)
    reasoner = Reasoner(world_model=world_model, search_config=config, search_algo=search_algo)

    evaluator = GSM8KEvaluator(output_extractor=utils.retrieve_answer,
                               answer_extractor=utils.retrieve_answer_from_dataset,
                               init_prompt=prompt,
                               sample_prompt_type="rap",
                               disable_log=disable_log,
                               disable_tqdm=disable_tqdm, samples=samples)

    accuracy = evaluator.evaluate(reasoner, num_shot=2, resume=resume, log_dir=log_dir, split=split)
    print(accuracy)


if __name__ == '__main__':
    import os
    import sys
    import json
    import warnings
    import fire

    def main(prompt: str,
             hf_path: str = 'microsoft/phi-2',
             batch_size: int = 1,
             useful_prompt: str = 'prompts/gsm8k/useful_examples.json',
             disable_log: bool = False,
             disable_tqdm: bool = False,
             split: str = 'test',
             **kwargs):
      
        with open(useful_prompt) as f:
            useful_prompt = json.load(f)
        with open(prompt) as f:
            prompt = json.load(f)
        base_model = VLLMModel(model=hf_path)
        rap_gsm8k(base_model=base_model,
                  useful_prompt=useful_prompt,
                  prompt=prompt,
                  batch_size=batch_size,
                  disable_log=disable_log,
                  disable_tqdm=disable_tqdm,
                  split=split,
                  **kwargs)


    fire.Fire(main)
