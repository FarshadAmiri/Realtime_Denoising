import demucs.separate

""" 
Models:

htdemucs: first version of Hybrid Transformer Demucs. Trained on MusDB + 800 songs. Default model.
htdemucs_ft: fine-tuned version of htdemucs, separation will take 4 times more time but might be a bit better. Same training set as htdemucs.
htdemucs_6s: 6 sources version of htdemucs, with piano and guitar being added as sources. Note that the piano source is not working great at the moment.
hdemucs_mmi: Hybrid Demucs v3, retrained on MusDB + 800 songs.
mdx: trained only on MusDB HQ, winning model on track A at the MDX challenge.
mdx_extra: trained with extra training data (including MusDB test set), ranked 2nd on the track B of the MDX challenge.
mdx_q, mdx_extra_q: quantized version of the previous models. Smaller download and storage but quality can be slightly worse.
SIG: where SIG is a single model from the model zoo.


--shifts:
performs multiple predictions with random shifts (a.k.a the shift trick) of the input and average them.
This makes prediction SHIFTS times slower. Don't use it unless you have a GPU.

--overlap:
The --overlap option controls the amount of overlap between prediction windows.
Default is 0.25 (i.e. 25%) which is probably fine. It can probably be reduced to 0.1 to improve a bit speed.
"""


from demucs.separate import main

model_name = "mdx_extra"
# model_name = "htdemucs"

input_file = r"D:\Git_repos\DeepNoiseReducer\noisy_auido_files\noisy_fish.wav"
output_dir = r"D:\Git_repos\DeepNoiseReducer\noisy_auido_files\demucs_results"

main([
    "--mp3",
    "--two-stems", "vocals",
    "-n", model_name,
    "--out", output_dir,
    "--shifts", "10",        # You can adjust the number of shifts as needed,
    "--overlap", "0.3",      # Reduce overlap for better speed (0.1 = 10%)
    input_file
])