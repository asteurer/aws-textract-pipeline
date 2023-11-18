"""
Adapted (stolen) from:  
- https://docs.aws.amazon.com/textract/latest/dg/examples-extract-kvp.html
- https://github.com/mludvig/amazon-textract-parser/issues/1
"""

import boto3
import csv
import time
from process_textract_response import process_detected_text, process_key_values

"""
If you need to troubleshoot the various JSON events/responses, use the code below:
import json
json_string = json.dumps(analyze_response)
bucket_name = 'conservice-biu-textract'
json_file_name = 'response.json'
s3_client.put_object(Body=json_string, Bucket=bucket_name, Key=json_file_name)
"""

textract_client = boto3.client('textract')
s3_client = boto3.client('s3')


def lambda_handler(event, context):
    
    event_record = event["Records"][0]["s3"]
    bucket_name = event_record["bucket"]["name"]
    file_name = event_record["object"]["key"]
    
    """
    Passing the file data to both document_analysis and document_text_detection
    and retrieving the job_id only so that they can be processed asynchronously.
    """
    analysis_job_response = textract_client.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': file_name
                }
            },
            FeatureTypes=['FORMS']
        )
        
    detect_job_response = textract_client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': file_name
                }
            }
        )
        
    
    detect_response = get_document_status(detect_job_response["JobId"], 'detect_text')
    analyze_response = get_document_status(analysis_job_response["JobId"], 'analyze')
    
    make_and_place_csv(detect_response, 'detect_text', bucket_name, file_name)
    make_and_place_csv(analyze_response, 'analyze', bucket_name, file_name)
    
    
    
def get_document_status(job_id, method, sleep_time=5):
    """
    Polls AWS Textract for the status of a document processing job until completion.

    :param textract_client: The AWS Textract client to use for requests.
    :param job_id: The job ID for the document processing request.
    :param method: The processing method, either 'analyze' or 'detect_text'.
    :param sleep_time: Time in seconds to wait between each poll. Default is 5.
    :return: A list of responses from the Textract client.
    """
    try:
        if method == 'analyze':
            client_method = textract_client.get_document_analysis
        elif method == 'detect_text':
            client_method = textract_client.get_document_text_detection
        else:
            raise ValueError(f"Invalid method: {method}. Choose 'analyze' or 'detect_text'.")

        responses_list = []
        response = client_method(JobId=job_id)
        responses_list.append(response)

        # Check initial job status
        if response['JobStatus'] == 'FAILED':
            raise RuntimeError(f"Textract job {job_id} failed.")

        # Continue polling as long as the job is in progress
        while response['JobStatus'] == 'IN_PROGRESS':
            time.sleep(sleep_time)
            response = client_method(JobId=job_id)
            if response['JobStatus'] == 'FAILED':
                raise RuntimeError(f"Textract job {job_id} failed.")
        
        responses_list.append(response)

        # If the job is complete but paginated, continue fetching the rest of the pages
        while 'NextToken' in response:
            response = client_method(JobId=job_id, NextToken=response['NextToken'])
            responses_list.append(response)
            if response['JobStatus'] == 'FAILED':
                raise RuntimeError(f"Textract job {job_id} failed.")

        return responses_list

    except Exception as e:
        # Consider logging the exception details here
        raise e
    
    
def make_and_place_csv(response, response_type, bucket_name, pdf_file_name):
    
    """
    Creates a CSV file and places it in the relevant S3 bucket directory
    
    :param response: The raw JSON response from Textract
    :param response_type: The name of the Textract service used (either 'detect_text' or 'analyze')analyze
    :param bucket_name: The name of the S3 bucket
    :param pdf_file_name: The S3 key for the retrieved PDF
    :return: None
    """

    filepath = "/tmp/"
    filename = ""
    pdf_file_name_elements = pdf_file_name.split("/")
    utility_folder = pdf_file_name_elements[-2]
    pdf_control_number = pdf_file_name_elements[-1].split(".")[0] # Removing the filepath and the extension from the filename
    
    if response_type == "detect_text":
        
        data = process_detected_text(response)
        filename = "detect_text.csv"
        filepath += filename
        
        with open(filepath, 'w', newline='') as csv_file:
            
            writer = csv.writer(csv_file)
            writer.writerow(["'Key", "'Value"])
            
            # This adds 'uncategorized' as the key name to make combining with the key_value document easier
            for entry in data:
                writer.writerow(["'uncategorized", f"{entry}"]) # The data from detect_text already comes with an "'"
                
    
    elif response_type == "analyze":
    
        data = process_key_values(response)
        filename = "analyze.csv"
        filepath += filename
        
        with open(filepath, 'w', newline='') as csv_file: 
            
            writer = csv.writer(csv_file)
            writer.writerow(["'Key", "'Value"])
            
            for key, value in data.items():
                key = f"'{key}" # Adding a "'" to the string to ensure it is read as a string
                
                for entry in value:
                    writer.writerow([key, f"'{entry}"])
        
    with open(filepath, 'rb') as file:
        s3_client.put_object(
            Bucket=bucket_name, 
            Key=f'csv_data/{utility_folder}/{pdf_control_number}/{filename}', 
            Body=file.read()
        )

    