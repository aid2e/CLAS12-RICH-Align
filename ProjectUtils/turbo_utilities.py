import numpy as np
import torch
import math
from dataclasses import dataclass
from ax.core.experiment import Experiment
from ax.core.trial_status import TrialStatus
from ax.generation_strategy.generation_node import GenerationNode
from ax.generation_strategy.external_generation_node import ExternalGenerationNode

from ax.core.data import Data
from ax.service.utils.report_utils import exp_to_df
from botorch.acquisition import qExpectedImprovement
from botorch.generation import MaxPosteriorSampling
from botorch.fit import fit_gpytorch_mll
from botorch.models import SingleTaskGP
from botorch.optim import optimize_acqf
from botorch.utils.transforms import unnormalize
from torch.quasirandom import SobolEngine
from gpytorch.likelihoods import GaussianLikelihood
from gpytorch.constraints import Interval
from gpytorch.kernels import MaternKernel, ScaleKernel
from gpytorch.mlls import ExactMarginalLogLikelihood
from botorch.acquisition.logei import (
    qLogExpectedImprovement,
)
from botorch.utils.transforms import unnormalize
from gpytorch.priors import LogNormalPrior, GammaPrior

# Based on BoTorch tutorial for TuRBO,
# https://botorch.org/docs/tutorials/turbo_1/,
# adapted for use in an Ax custom generation node

@dataclass
class TurboState:
    dim: int
    batch_size: int
    length: float = 0.8
    length_min: float = 0.5**7
    length_max: float = 1.6
    failure_counter: int = 0
    success_counter: int = 0
    success_tolerance: int = 10
    failure_tolerance: int = None
    best_value: float = -float("inf")
    restart_triggered: bool = False
    def __post_init__(self):
        self.failure_tolerance = math.ceil(max(4.0/self.batch_size, self.dim/self.batch_size))
        self.trust_regions = []

def update_state(state: TurboState, Y_next: torch.Tensor) -> TurboState:
    if Y_next.max().item() > state.best_value + 1e-3 * abs(state.best_value):
        state.success_counter += 1
        state.failure_counter = 0
    else:
        state.success_counter = 0
        state.failure_counter += 1
    if state.success_counter >= state.success_tolerance:
        state.length = min(2.0 * state.length, state.length_max)
        state.success_counter = 0
    elif state.failure_counter >= state.failure_tolerance:
        state.length /= 2.0
        state.failure_counter = 0
    state.best_value = max(state.best_value, Y_next.max().item())
    if state.length < state.length_min:
        state.restart_triggered = True
    return state

def generate_batch(
    state: TurboState,
    model,
    X: torch.Tensor,
    Y: torch.Tensor,
    batch_size: int,
    bounds: torch.Tensor,
    acqf: str = "ei",
    num_restarts: int = 50,
    raw_samples: int = 512,
    n_candidates: int = None,
    parameters: dict = None
) -> torch.Tensor:
    if parameters is None:
        parameters = {}
    
    # X, Y in normalized [0,1]^d
    assert X.min() >= 0.0 and X.max() <= 1.0
    if n_candidates is None:
        n_candidates = min(5000, max(2000, 200 * X.shape[-1]))
    d = X.shape[-1]
    # Trust region bounds
    # TODO: use point with largest posterior mean
    x_center = X[Y.argmax(), :].clone()
    lengthscale = model.covar_module.base_kernel.lengthscale.detach().squeeze()
    weights = lengthscale / lengthscale.mean()
    weights = weights / torch.prod(weights.pow(1.0 / d))
    tr_lb = torch.clamp(x_center - weights * state.length / 2.0, 0.0, 1.0)
    tr_ub = torch.clamp(x_center + weights * state.length / 2.0, 0.0, 1.0)

    tr_lb_denorm = unnormalize(tr_lb.unsqueeze(0), bounds).squeeze(0)
    tr_ub_denorm = unnormalize(tr_ub.unsqueeze(0), bounds).squeeze(0)

    # track trust region size, for visualization
    names = list(parameters.keys())
    for i, name in enumerate(names):
        print(f"{name:15s}  [{tr_lb_denorm[i]:8.4f}, {tr_ub_denorm[i]:8.4f}]")

    record = {f"{n}_low": float(tr_lb_denorm[i]) for i,n in enumerate(names)}
    record.update({f"{n}_high": float(tr_ub_denorm[i]) for i,n in enumerate(names)})
    state.trust_regions.append(record)
    
    if acqf == "ts":
        sobol = SobolEngine(dimension=d, scramble=True)
        pert = sobol.draw(n_candidates).to(X)
        pert = tr_lb + (tr_ub - tr_lb) * pert
        prob_perturb = min(20.0/d, 1.0)
        mask = torch.rand(n_candidates, d, dtype=X.dtype, device=X.device) <= prob_perturb

        idx = torch.where(mask.sum(dim=1) == 0)[0]
        mask[idx, torch.randint(0, d, (len(idx),), device=X.device)] = 1
        X_cand = x_center.expand(n_candidates, d).clone()
        X_cand[mask] = pert[mask]
        thompson = MaxPosteriorSampling(model=model, replacement=False)
        with torch.no_grad():
            X_next = thompson(X_cand, num_samples=batch_size)
    else:
        ei = qLogExpectedImprovement(model=model, best_f=Y.max())
        X_next, _ = optimize_acqf(
            ei,
            bounds=torch.stack([tr_lb, tr_ub]),
            q=batch_size,
            num_restarts=num_restarts,
            raw_samples=raw_samples,
        )
    # Unnormalize to original domain
    X_denorm = unnormalize(X_next, bounds)
    return X_denorm

@dataclass(init=False)
class TuRBOGenerationNode(ExternalGenerationNode):
    """
    Ax ExternalGenerationNode implementing TuRBO per BoTorch tutorial
    (tutorial at https://botorch.org/docs/tutorials/turbo_1/).
    Assumes initial Sobol or warm-up samples are present under `name_lastnode`.
    """
    def __init__(
        self,
        batch_size: int,
        name: str,
        name_lastnode: str,
        acqf: str = "ei",
        num_restarts: int = 50,
        raw_samples: int = 512,
        transition_criteria=None,
        turbo_state = None,
    ) -> None:
        super().__init__(node_name=name, transition_criteria=transition_criteria)
        self.batch_size = batch_size
        self.name = name
        self.name_lastnode = name_lastnode
        self.acqf = acqf
        self.num_restarts = num_restarts
        self.raw_samples = raw_samples
        self.state = turbo_state #: TurboState | None = None
        self.dim: int | None = None
        self.bounds: torch.Tensor | None = None
        self.X_turbo: torch.Tensor | None = None
        self.Y_turbo: torch.Tensor | None = None
        self.parameters: Optional[List[RangeParameter]] = None
        self.candidate_num = 0
        self.candidates = None
        self.statelist = []
    @property
    def model_to_gen_from_name(self) -> str:
        return self.name

    def update_generator_state(self, experiment: Experiment, data: Data) -> None:
        if self.candidate_num < self.batch_size and self.candidates is not None:
            return
        # Capture search space and extract history
        print("Updating state")
        search_space = experiment.search_space
        params = search_space.parameters
        self.parameters = search_space.parameters
        metric = list(experiment.optimization_config.metrics.keys())[0]
        exp_df = exp_to_df(experiment)
        
        X_list, Y_list, Y_list_err = [], [], []
        for t_idx, trial in experiment.trials.items():            
            if trial.status == TrialStatus.COMPLETED:
                gen = exp_df.loc[exp_df.trial_index == t_idx, "generation_method"].item()
                if gen in {self.name_lastnode, self.name, "Manual"}:
                    p = trial.arm.parameters
                    x = np.array([p[k] for k in params.keys()])                    
                    
                    y = data.df.loc[
                        (data.df.trial_index==t_idx)&(data.df.metric_name==metric),
                        "mean"
                    ].item()
                    yerr = data.df.loc[
                        (data.df.trial_index==t_idx)&(data.df.metric_name==metric),
                        "sem"
                    ].item()
                    X_list.append(x)
                    Y_list.append(-1.0*y)
                    Y_list_err.append(yerr)
        X_np = np.vstack(X_list)
        Y_np = np.array(Y_list)
        Y_err_np = np.array(Y_list_err)
        
        # Initialize dimension and bounds on first call
        if self.dim is None:
            print("self.dim is none")
            self.dim = X_np.shape[1]
            lb = torch.tensor([p.lower for p in params.values()])
            ub = torch.tensor([p.upper for p in params.values()])
            self.bounds = torch.stack([lb, ub])
        # Normalize to [0,1]
        lb_np = np.array([p.lower for p in params.values()])
        ub_np = np.array([p.upper for p in params.values()])
        X_norm = (X_np - lb_np) / (ub_np - lb_np)
        X_norm = np.clip(X_norm, 0.0, 1.0)
        
        param_names = list(params.keys())
        mins = X_np.min(axis=0)
        maxs = X_np.max(axis=0)
        
        X_t = torch.tensor(X_norm, dtype=torch.double)
        Y_t = torch.tensor(Y_np, dtype=torch.double).unsqueeze(-1)
        Y_e = torch.tensor(Y_err_np, dtype=torch.double).unsqueeze(-1)
        
        # Initialize or update Turbo state
        if self.state is None:
            self.state = TurboState(dim=self.dim, batch_size=self.batch_size, best_value=Y_np.max())
        self.state = update_state(self.state, Y_t[-self.batch_size:])
        print("State: ", self.state)
        # Fit GP on normalized data
        # Standardize Y
        Ym, Ys = Y_t.mean(), Y_t.std()
        Y_std = (Y_t - Ym) / Ys
        Y_var = (Y_e / Ys) ** 2

        covar = ScaleKernel(MaternKernel(nu=2.5,ard_num_dims=self.dim,
                                         lengthscale_prior=LogNormalPrior(0.0, 0.5)
                                         ), 
                            outputscale_prior=GammaPrior(1.0, 0.15),
                            lengthscale_constraint=Interval(0.0001,4.0)
                            )

        lik = GaussianLikelihood()
        gp = SingleTaskGP(X_t, Y_std, Y_var, covar_module=covar, likelihood=lik)
        mll = ExactMarginalLogLikelihood(gp.likelihood, gp)
        
        fit_gpytorch_mll(mll)
        # Evaluate GP fit
        gp.eval()
        with torch.no_grad():
            post = gp.posterior(X_t, observation_noise=True)
            mu = post.mean.squeeze(-1)
            var = post.variance.squeeze(-1)
            
        y_std = Y_std.squeeze(-1)
        resid = y_std - mu
        rmse_std = torch.sqrt((resid**2).mean())
        std_resid = resid / var.clamp_min(1e-12).sqrt()
        cov95 = ((y_std >= mu - 1.96*var.sqrt()) & (y_std <= mu + 1.96*var.sqrt())).float().mean()
        nlpd = 0.5*torch.log(2*torch.pi*var) + 0.5*(resid**2)/var
        nlpd_mean = nlpd.mean()
        
        mu_orig = mu * Ys + Ym
        var_orig = var * (Ys**2)
        resid_orig = Y_t.squeeze(-1) - mu_orig
        rmse_orig = torch.sqrt((resid_orig**2).mean())
        
        try:
            from scipy.stats import spearmanr
            rho, _ = spearmanr(mu_orig.cpu().numpy(), Y_t.squeeze(-1).cpu().numpy())
        except Exception:
            rho = float('nan')

        print(f"[GP eval] rmse_std={rmse_std.item():.3f} rmse_orig={rmse_orig.item():.3f} "
              f"cov95={cov95.item():.3f} nlpd={nlpd_mean.item():.3f} spearman_rho={rho:.3f}")
        
        # Generate next TuRBO batch (in denormalized domain)
        X_next = generate_batch(
            state=self.state,
            model=gp,
            X=X_t,
            Y=Y_std,
            batch_size=self.batch_size,
            bounds=self.bounds,
            acqf=self.acqf,
            num_restarts=self.num_restarts,
            raw_samples=self.raw_samples,
            parameters=params
        )
        self.candidates = X_next.numpy()
        self.candidate_num = 0
        return
    
    def get_next_candidate(self, pending_parameters=None):
        print("Getting candidate")
        x = self.candidates[self.candidate_num]
        candidate = {
            p_name: x[i]
            for i, p_name in enumerate(self.parameters.keys())
        }
        self.candidate_num += 1
        return candidate
