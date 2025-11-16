import pytesseract
from pdf2image import convert_from_path
import os
import re

def preprocess_image(image, enhancement_level='high'):
    """
    Preprocess image to improve OCR accuracy
    
    Args:
        image: PIL Image object
        enhancement_level: 'high' for aggressive enhancement (better for poor quality),
                          'medium' for moderate enhancement (default),
                          'light' for minimal enhancement (good quality scans)
    """
    from PIL import ImageEnhance, ImageFilter
    import numpy as np
    from PIL import Image
    
    # Convert to grayscale
    image = image.convert('L')
    
    # Set enhancement parameters based on level
    if enhancement_level == 'high':
        contrast_factor = 2.5
        sharpness_factor = 3.0
        denoise_size = 3
    elif enhancement_level == 'medium':
        contrast_factor = 2.0
        sharpness_factor = 2.0
        denoise_size = 3
    else:  # light
        contrast_factor = 1.5
        sharpness_factor = 1.5
        denoise_size = 0
    
    # Increase contrast - helps distinguish similar characters
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(contrast_factor)
    
    # Increase sharpness - critical for 1 vs 4 distinction
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(sharpness_factor)
    
    # Apply slight denoising
    if denoise_size > 0:
        image = image.filter(ImageFilter.MedianFilter(size=denoise_size))
    
    # Binarization (convert to black and white)
    # This often significantly improves OCR and character distinction
    img_array = np.array(image)
    
    # Use Otsu-like adaptive thresholding for better binarization
    threshold = np.mean(img_array) * 0.88  # Slightly darker threshold
    img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
    image = Image.fromarray(img_array)
    
    # Optional: Apply morphological operations to clean up characters
    # Uncomment if needed - can help but may slightly affect layout
    # image = image.filter(ImageFilter.MaxFilter(3))  # Slight dilation
    # image = image.filter(ImageFilter.MinFilter(3))  # Slight erosion
    
    return image

def ocr_extract_txt(pdf_path, output_txt_path, dpi=600):
    """
    Alternative version with better layout preservation
    """
    if os.path.exists(pdf_path):
        file_name = os.path.basename(pdf_path)
        try:
            print("Converting PDF to images...")
            images = convert_from_path(pdf_path, dpi=dpi)
            
            all_text = []
            
            for i, image in enumerate(images):
                print(f"Processing page {i + 1}/{len(images)}")
                
                # Image preprocessing for better OCR
                #image = preprocess_image(image, enhancement_level='high')

                # PSM 4: Single column of text of variable sizes
                # This often works better for maintaining layout
                custom_config = r'--oem 3 --psm 4 -c preserve_interword_spaces=1'
                
                text = pytesseract.image_to_string(image, config=custom_config)
                
                if i > 0:
                    all_text.append(f"\n\n###> {file_name} | PAGE-{i + 1} <###\n\n")
                else:
                    all_text.append(f"###> {file_name} | PAGE-{i + 1} <###\n\n")
                
                all_text.append(text)
            
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(''.join(all_text))
            
            print(f"OCR completed! Text saved to: {output_txt_path}")

            return ''.join(all_text)
            
        except Exception as e:
            print(f"Error during OCR: {str(e)}")
    else:
        print(f"PDF file not found: {pdf_file}")
        print("Please update the pdf_file variable with the correct path")

def legacy_normalize_layout(text: str):
    '''
    Some lockup lists contain weird spacing when run through the extract layout function. 

    This function handles multiple spaces between characters and known repeat words to allow for normal search functions. 
    '''
    formatted = re.sub(r'(?<=\w|\d|[,.]) {2}(?=\w|\d)', ' ', text)
    formatted = re.sub(r'(?<=year)(\s+)(?=old)', ' ', formatted)
    formatted = re.sub(r'(?<=Black)(\s+)(?=or)', ' ', formatted)
    formatted = re.sub(r'(?<=or)(\s+)(?=African-American)', ' ', formatted)
    formatted = re.sub(r'(?<=or)(\s+)(?=Latino)', ' ', formatted)
    formatted = re.sub(r'(?<=Hispanic)(\s+)(?=or)', ' ', formatted)
    formatted = re.sub(r'(?<=Assigned)(\s+)(?=to)', ' ', formatted)
    formatted = re.sub(r'(?<=,)(\s+)(?=\w)', ' ', formatted)
    # ^ all the above fixes multiple spaces especially between words used to help find other info e.g. name searches
    formatted = re.sub(r'(?<=\n)\n(?=               )',
                       '', formatted)  # fixes blank lines
    # fixes additional blank lines from the fixing blank lines
    formatted = re.sub(r'(?<=\n)\n(?=               )', '', formatted)
    formatted = re.sub(r'—|•', '', formatted)
    # formatted = re.sub(r'(?<=     )[0-9]{6}     (?!\n)', r'[0-9]{6}\n', formatted)

    return formatted


def legacy_extract_txt(pdf_path, output_txt_path):
    '''
    Takes PDF

    Returns list of strings containing the text of each page. 
    '''
    from pypdf import PdfReader

    if os.path.exists(pdf_path):
        try:
            all_text = []
            file_name = os.path.basename(pdf_path)
            read_pdf = PdfReader(pdf_path)
            
            for i, page in enumerate(read_pdf.pages):
                raw_page_text = page.extract_text(extraction_mode="layout")

                formatted_page = legacy_normalize_layout(raw_page_text)

                all_text.append(f"\n\n###> {file_name} | PAGE-{i + 1} <###\n\n")

                all_text.append(formatted_page)

            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(''.join(all_text))
                    
            print(f"OCR completed! Text saved to: {output_txt_path}")
            
            return ''.join(all_text)
                
        except Exception as e:
            print(f"Error during Legacy text extraction: {str(e)}")
            
    else:
        print(f"PDF file not found: {pdf_file}")
        print("Please update the pdf_file variable with the correct path")

if __name__ == '__main__':
    test_path = "/Users/viviennemonteiro/Projects/DC Courtwatch/july_lists/20250705090036.pdf"
    new_output_path = "/Users/viviennemonteiro/Projects/DC Courtwatch/lockupscraper/LockUpScraper2.0/output/new_test_output.txt"
    legacy_output_path = "/Users/viviennemonteiro/Projects/DC Courtwatch/lockupscraper/LockUpScraper2.0/output/legacy_test_output.txt"

    legacy_extract_txt(test_path, legacy_output_path)
    ocr_extract_txt(test_path, new_output_path)

