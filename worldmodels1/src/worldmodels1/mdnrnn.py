import torch
import torch.nn as nn
import torch.optim as optim

class MDN(nn.Module):
    def __init__(self, n_hidden, n_gaussians, latent_dim):
        self.n_gaussians = n_gaussians
        self.latent_dim = latent_dim
        super(MDN, self).__init__()
        self.z_h = nn.Sequential(
            nn.Linear(n_hidden, 128),
            nn.ReLU(),
            nn.Linear(128, n_gaussians * 3 * latent_dim)
        )
        self.first = True
    def forward(self, x):         
        z_h = self.z_h(x)
        pi, mu, sigma = torch.split(z_h, self.n_gaussians * self.latent_dim, dim=2)
        pi = nn.Softmax(dim=1)(pi)
        sigma = torch.exp(sigma)
        if self.first:
            print(f'lstm output/mdn input shape: {x.shape}')
            print(f'z_h shape: {z_h.shape}')
            print(f'pi shape: {pi.shape}')
            print(f'mu shape: {mu.shape}')
            print(f'sigma shape: {sigma.shape}')
            self.first = False
        return pi, mu, sigma

class MemoryModel(nn.Module):
    def __init__(self, n_input, n_hidden, n_gaussians, latent_dim):
        super(MemoryModel, self).__init__()
        self.lstm = nn.LSTM(n_input, n_hidden, batch_first=True)
        self.mdn = MDN(n_hidden, n_gaussians, latent_dim)
        self.first = True

    def forward(self, x):
        if self.first:
            print(f'input shape: {x.shape}')
            self.first = False
        lstm_out, _ = self.lstm(x)
        pi, mu, sigma = self.mdn(lstm_out)
        return pi, mu, sigma

