# Prompt Image Search

OpenAI Clip is used to sort images based on a text prompt for their visual content, not filenames or metadata, returning the top-10 results.  
Results are ranked by cosine similarity and can be clicked to open directly into Windows Explorer.  
A major use case is locating specific photos in massive, poorly named collections by simply describing the scene with a prompt.  
It is useful for those who need to quickly sort through screenshots, or other photos, by searching with visual content in mind.  

## Requirements

Python 3.10+ and NVIDIA GPU  
HuggingFace User Access Token (Read Perms)  
PyTorch with CUDA  

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu132
pip install open_clip_torch pillow huggingface_hub
hf auth login

python PromptImgSearch.py
```  

*Supported image formats include `PNG, JPG, JPEG, GIF, BMP, WEBP, and TIFF`*  
*Intended for usage with Windows*  

## Usage Instructions

The model will load in the background while the user interface opens.  
Enter a text description of the visual content of your image in the Search Prompt box.  
Select your search location from the options of all drives, single drive, or base folder.  
Click the Start Search button to recursively scan the selected location and update the top-10 matches.  
Clicking any of the final displayed results will open its file location in Windows Explorer.
