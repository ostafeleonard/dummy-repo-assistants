import os
from pdf2image import convert_from_path
import time
import shutil
import string

from logger.logger import logger
from config import config


class ConvertorPDF2PNG():
    def __init__(self):
        self.max_nr_pdf_pages_to_process = config.settings['convertor_pdf_2_png']['max_nr_pdf_pages_to_process']
        self.supported_formats = self.get_supported_formats(config.settings['convertor_pdf_2_png']['supported_formats'])
        self.output_image_format = config.settings['convertor_pdf_2_png']['output_image_format']

        self.failed_to_convert = config.settings['convertor_pdf_2_png']['failed_to_convert']
        self.pdf_files = config.settings['convertor_pdf_2_png']['pdf_files']
        self.png_files = config.settings['convertor_pdf_2_png']['output_png_files_path']

        self.dpi = config.settings['convertor_pdf_2_png']['dpi']
        self.thread_count = config.settings['convertor_pdf_2_png']['thread_count']
        self.last_page = config.settings['convertor_pdf_2_png']['limit_images']

        self.output_file = ''
        self.output_files = []

    def convert_pdf_file_to_png_files(self, pdf_file_path: str = '', output_path: str = '') -> int:
        '''
        Convert pdf file to png files. Returns the converted files.
        If the file is not a pdf or does not exist, returns an empty list.
        If the file is a pdf, but cannot be converted, moves the file to the failed_to_convert directory.
        '''

        if not self.validate_input_file(pdf_file_path):
            logger.log_debug(f'{__name__} - convert_to_pdf - Cannot process file: {pdf_file_path}')
            return '', ''
        pdf_file_path = self.remove_special_characters_from_filename(pdf_file_path)
        logger.log_info(f'{__name__} - convert_pdf_file - Processing file: {pdf_file_path}')

        self.create_directory(output_path)
        output_pdf_images_names = self.get_output_pdf_image_names(pdf_file_path)
        images = self.convert_pdf_from_path(pdf_file_path)
        output_files = self.process_poppeller_output(images, output_pdf_images_names, output_path)
        if output_files == []:
            logger.log_warning(f'{__name__} - convert_pdf_file - There are no images converted from pdf: {pdf_file_path}')
            self.move_processed_pdf(pdf_file_path, output_path + '/' + self.failed_to_convert)
            return pdf_file_path, output_files
        
        self.move_processed_pdf(pdf_file_path, output_path + '/' + self.pdf_files)
        return pdf_file_path, output_files

    def convert_pdf_from_path(self, input_pdf_path: str = '') -> list:
        '''
        Convert pdf to png. Returns a list with images.
        '''
        images = []
        try:
            images = convert_from_path(
                pdf_path = input_pdf_path,
                dpi = self.dpi,
                thread_count = self.thread_count,
                last_page = self.last_page
            )
        except Exception as e:
            logger.log_error(f'{__name__} - convert_to_png - Cannot convert to png: {input_pdf_path} Error {e}')
        return images

    def get_output_pdf_image_names(self, file_path: str = '') -> str:
        '''
        Getting the output pdf images names format
        '''
        file_names = '.'.join(file_path.replace('\\', '/').split('/')[-1].split('.')[:-1])
        return file_names + '-pdf-page{0}_from_{1}.' + self.output_image_format

    def get_output_directory(self, file_path: str = '') -> str:
        '''
        Getting the output directory
        '''
        return '/'.join(file_path.replace('\\', '/').split('/')[:-1])

    def process_poppeller_output(self, images: list, images_names: list, output_path: str) -> list:
        '''
        Process the poppeller output.
        '''
        logger.log_debug(f'{__name__} - process_poppeller_output - Total resulted images: {len(images)}')
        output_images = []
        if images == []:
            logger.log_warning(f'{__name__} - process_poppeller_output - There are no images to convert. Total images: {len(images)}')
            return output_images
        pdf_max_page_number = len(images)
        output_path = output_path + '/' + self.png_files
        self.create_directory(output_path)
        for page_number in range(len(images)):
            output_image_name = output_path + '/' + images_names.format(page_number + 1, pdf_max_page_number)
            try:
                logger.log_info(f'{__name__} - process_poppeller_output - Creating image: {output_image_name}')
                images[page_number].save(output_image_name)
                output_images.append(output_image_name)
            except Exception as e:
                logger.log_error(f'{__name__} - process_poppeller_output - Cannot process image: {images}. Error: {e}')
                break
            if len(output_images) >= self.max_nr_pdf_pages_to_process:
                logger.log_warning(f'{__name__} - process_poppeller_output - Max nr pages excedded.. Total PDF pages: {len(images)} Total Pages processed: {len(output_images)}')
                break
        return output_images
    
    def get_supported_formats(self, supported_formats: list) -> list:
        '''
        Get the supported formats.
        '''
        if not supported_formats:
            logger.log_warning(f'{__name__} - get_supported_formats - Empty supported formats list')
            return []
        return [file_format.lower() for file_format in supported_formats]
    
    def validate_input_file(self, pdf_file_path: str = '') -> bool:
        '''
        Validate the input file. 
        Checking if the file exists and if the file extension is in the supported formats.
        '''
        if not os.path.isfile(pdf_file_path):
            logger.log_warning(f'{__name__} - validate_input_file - File does not exist: {pdf_file_path}')
            return False
        return pdf_file_path.split('.')[-1].lower() in self.supported_formats

    def move_processed_pdf(self, input_file_path: str = '', output_path: str = '') -> None:
        '''
        Move the processed pdf file to the output path.
        '''

        if not os.path.isfile(input_file_path):
            logger.log_info(f'{__name__} - move_processed_pdf - File does not exist: {input_file_path}')
            return
        self.create_directory(output_path)
        try:
            logger.log_info(f'{__name__} - move_processed_pdf - Moving file: {input_file_path} to {output_path}')
            shutil.move(input_file_path, output_path)
        except Exception as e:
            logger.log_error(f'{__name__} - move_processed_pdf - Cannot move file {input_file_path} to {output_path} Error: {e}')
            self.move_processed_pdf(input_file_path, output_path + '/fail_to_move/' + str(int(time.time() * 1000)))
    
    def create_directory(self, directory_path: str = '') -> None:
        '''
        Creating directory if it does not exist.
        '''
        if not os.path.isdir(directory_path):
            logger.log_info(f'{__name__} - create_directory - Creating directory: {directory_path}')
            os.makedirs(directory_path)

    def remove_special_characters_from_filename(self, input_file_path: str = '') -> str:
        '''
        Cleaning the file name from unknown characters.
        '''
        if not os.path.isfile(input_file_path):
            return input_file_path
        path_to_file = '/'.join(input_file_path.replace('\\', '/').split('/')[:-1])
        file_name = input_file_path.replace('\\', '/').split('/')[-1]

        list_with_used_characters = list(string.digits + string.ascii_lowercase + string.ascii_uppercase + string.punctuation)
        try:
            unique_characters = list(set(file_name))
        except Exception as e:
            return input_file_path
        for character in unique_characters:
            if character in list_with_used_characters:
                continue
            file_name = file_name.replace(character, '_')
        
        new_file_name = path_to_file + '/' + file_name
        os.rename(input_file_path, new_file_name)

        if not os.path.isfile(new_file_name):
            return input_file_path
        return new_file_name
   

if __name__ == '__main__':
    pdf_2_png = ConvertorPDF2PNG()
    path_to_pdf_file = 'SCAN_20231009_164520471.pdf'
    output_path = 'SCAN_20231009_164520471/'
    pdf_file_path, output_files = pdf_2_png.convert_pdf_file_to_png_files(pdf_file_path = path_to_pdf_file, output_path = output_path)
    print('Ouput: ', pdf_file_path, output_files)
