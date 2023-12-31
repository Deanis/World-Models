import argparse
from cnnvae import VAE
import torch
import numpy as np
from tqdm import tqdm
from utils import get_dataloader
import logging
import os

os.environ['CUDA_VISIBLE_DEVICES'] = '0'

def main(args):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logging.info('Starting the script...')
    
    data_path = args.data_path
    batch_size = args.batch_size
    num_workers = args.num_workers

    logging.info(f'Using data path: {data_path}, batch size: {batch_size}, number of workers: {num_workers}')

    logging.info(f'Loading data from {data_path}')
    try:
        preprocessed_data = np.load(data_path, allow_pickle=True)
        logging.info('Data loaded successfully.')
    except Exception as e:
        logging.error(f'Error while loading data: {e}')
        return

    logging.info('Initializing dataset and dataloader...')
    try:
        dataloader = get_dataloader(preprocessed_data, batch_size, num_workers, get_action=True, shuffle=args.shuffle, get_metadata=args.get_metadata)
        logging.info('Dataset and dataloader initialized successfully.')
    except Exception as e:
        logging.error(f'Error while initializing dataset and dataloader: {e}')
        return

    logging.info('Loading VAE model...')
    try:
        vae = VAE()
        state_dict = torch.load(args.vae_path, map_location=torch.device('cuda'))
        # Remove 'module.' prefix from state_dict keys
        new_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        vae.load_state_dict(new_state_dict)

        vae = vae.to(device="cuda")
        vae.eval()
        logging.info('VAE model loaded successfully.')
    except Exception as e:
        logging.error(f'Error while loading VAE model: {e}')
        return

    latent_action_pairs = []

    logging.info('Generating latent vectors...')
    try:
        first_run = True  # flag variable to print details about the first batch
        with torch.no_grad():
            with tqdm(total=len(dataloader), desc='Creating latent vectors', unit='batch') as pbar:
                for idx, batch in enumerate(dataloader):
                    #logging.info(f'Processing batch {idx+1}')
                    if first_run:
                        # Print details about the batch
                        logging.info(f'Batch size: {len(batch[0])}')
                        logging.info(f'Batch shape: {[t[0].shape for t in batch]}') 
                        logging.info(f'Image shape: {batch[0][0].shape}')
                        logging.info(f'Action shape: {batch[1][0].shape}')
                        if args.get_metadata:
                            logging.info(f'Data from episode: {batch[2][0]}')
                            logging.info(f'Data from step: {batch[3][0]}, to step: {batch[3][-1]}')
                        first_run = False  # update the flag variable

                    # log episode and step count
                    if args.get_metadata:
                        #logging.info(f'Data from episode: {batch[2][0]}, Data from step: {batch[3][0]}')
                        #print(f'Data from episode: {batch[2][:]}, Data from step: {batch[3][:]}')
                        episodes = batch[2].cpu().numpy()
                        steps = batch[3].cpu().numpy()
                
                    states = torch.stack([s for s in batch[0]]).to(device="cuda")
                    actions = torch.stack([a for a in batch[1]]).cpu().numpy()

                    mu, logvar = vae.encode(states)
                    z = vae.reparameterize(mu, logvar)

                    latent_vectors = z.cpu().numpy()
                    if args.get_metadata:
                        for latent, action, episode, step in zip(latent_vectors, actions, episodes, steps):
                            #print(f'Latent shape: {latent.shape}, action shape: {action.shape}, episode shape: {episode.shape}, step shape: {step.shape}')
                            #print(f'Latent: {latent}, action: {action}, episode: {episode}, step: {step}')
                            latent_action_pairs.append(np.concatenate([latent.astype(np.float16), action.astype(np.float16), [episode.astype(np.float16)], [step.astype(np.float16)]]))
                    else:    
                        for latent, action in zip(latent_vectors, actions):
                            latent_action_pairs.append(np.concatenate([latent.astype(np.float16), action.astype(np.float16)]))
                    pbar.update(1)
        logging.info('Latent vectors generated successfully.')
        # Save the latent vectors
        logging.info(f'Saving latent vectors to {args.output_path}')
        np.save(args.output_path, latent_action_pairs)
        logging.info('Latent vectors saved successfully.')

    except Exception as e:
        logging.error(f'Error while generating latent vectors: {e}')
        return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate latent vectors using a pretrained VAE model.')
    parser.add_argument('--data_path', type=str, default='data/collected_data.npy', help='Path to the data file.')
    parser.add_argument('--vae_path', type=str, default='vae.pth', help='Path to the pretrained VAE model.')
    parser.add_argument('--output_path', type=str, default='latent_action_pairs.npy', help='Path to the output file.')
    parser.add_argument('--batch_size', type=int, default=1000, help='Batch size for the dataloader.')
    parser.add_argument('--num_workers', type=int, default=0, help='Number of worker threads for the dataloader.')
    parser.add_argument('--shuffle', action='store_true', help='Whether to shuffle the data or not.')
    parser.add_argument('--get_metadata', action='store_true', help='Whether to get metadata or not.')

    args = parser.parse_args()
    
    main(args)
