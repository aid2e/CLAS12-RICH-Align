from ax.generation_strategy.transition_criterion import MinTrials
from ax.generation_strategy.transition_criterion import MaxGenerationParallelism
from ax.core.trial_status import TrialStatus

from ax.generation_strategy.generation_strategy import GenerationStrategy
from ax.generation_strategy.generation_node import GenerationNode
from ax.generation_strategy.model_spec import GeneratorSpec
from ax.modelbridge.registry import Generators
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.core.problem import Problem
from ProjectUtils.turbo_utilities import TuRBOGenerationNode, TurboState
# now test setting up generation strategy

def construct_generation_strategy(
        n_sobol, n_turbo,
        n_batch_sobol, n_batch_turbo 
) -> GenerationStrategy:
    
    """Constructs SOBOL/TuRBO gen strategy  
    """
    nodes = []
    # first, SOBOL node
    sobol_node = GenerationNode(
        node_name="Sobol",
        model_specs=[
            GeneratorSpec(
                model_enum=Generators.SOBOL,
                # Let's use model_kwargs to set the random seed.
                model_kwargs={"seed": 0},
            ),
        ],
        transition_criteria=[
            # Transition to BoTorch node once there are 5 trials on the experiment.
            MinTrials(
                threshold=n_sobol,
                transition_to="TuRBONode",
                use_all_trials_in_exp=True,
            )
            #,
            #MaxGenerationParallelism(n_batch_sobol)
        ]
    )
    if n_sobol > 0: # if we are loading initialization from a previous experiment
        nodes.append(sobol_node)
    
    turbo_node = TuRBOGenerationNode(n_batch_turbo,"TuRBONode","Sobol","ei",10,512,transition_criteria=[
                                             #MaxGenerationParallelism(n_batch_turbo)
                                         ]
    )
    nodes.append(turbo_node)
    return GenerationStrategy(
        name=f"turbo_gen_strat",
        nodes = nodes
    )

def construct_turbo_generation_strategy(
        n_turbo,
        n_batch_turbo,
        previous_state
) -> GenerationStrategy:
    
    """Constructs SOBOL/TuRBO gen strategy  
    """
    nodes = []
    # TODO: Save this and load it directly...
    #previous_state = TurboState(dim=30,batch_size=15,length=0.2,length_min=0.0078125, length_max=1.6, failure_counter=1, success_counter=0, success_tolerance=10, failure_tolerance=2, best_value=-5.295719671313375, restart_triggered=False)
    turbo_node = TuRBOGenerationNode(n_batch_turbo,"TuRBONode","Sobol","ei",10,512,transition_criteria=[],turbo_state=previous_state
                                     )
    nodes.append(turbo_node)
    return GenerationStrategy(
        name=f"turbo_gen_strat",
        nodes = nodes
    )
