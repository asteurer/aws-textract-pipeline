from collections import defaultdict

def process_detected_text(response_array):
    
    """
    Takes the array of detect_text JSON responses from Textract and processes 
    them into an array. 
    
    :return: Returns an array of arrays, [[key, value]]
    """
    
    output = []
    
    for json_object in response_array:
        
        if "Blocks" in json_object:
            
            blocks = json_object["Blocks"]
        
            for entry in blocks:
                blocktype = entry["BlockType"]
                
                if blocktype == 'LINE':
                      output.append(f"""'{entry["Text"]}""")
    
    return output
    
"""
The code below is only for processing the document_analysis response.
"""

def process_key_values(response_array):
    
    """
    :return: A defaultdict containing key-value pairs.
    """
    
    key_map, value_map, block_map = get_kv_map(response_array)

    # Get Key Value relationship
    return get_kv_relationship(key_map, value_map, block_map)


def get_kv_map(response_array):
    
    """
    :return: Three dictionaries containing the relevant keys, values, and blocks
    """
    
    key_map = {}
    value_map = {}
    block_map = {}
    
    
    for json_object in response_array:
        # Get the text blocks
        if "Blocks" in json_object:
            
            blocks = json_object['Blocks']
        
            # get key and value maps
            for block in blocks:
                block_id = block['Id']
                block_map[block_id] = block
                if block['BlockType'] == "KEY_VALUE_SET":
                    if 'KEY' in block['EntityTypes']:
                        key_map[block_id] = block
                    else:
                        value_map[block_id] = block

    return key_map, value_map, block_map
    

def get_kv_relationship(key_map, value_map, block_map):
    
    kvs = defaultdict(list)
    
    for block_id, key_block in key_map.items():
        
        value_block = find_value_block(key_block, value_map)
        key = get_text(key_block, block_map)
        val = get_text(value_block, block_map)
        
        kvs[key].append(val)
        
    return kvs


def find_value_block(key_block, value_map):
    
    for relationship in key_block['Relationships']:
        
        if relationship['Type'] == 'VALUE':
            
            for value_id in relationship['Ids']:
                
                value_block = value_map[value_id]
                
    return value_block


def get_text(result, blocks_map):
    
    text = ''
    
    if 'Relationships' in result:
        
        for relationship in result['Relationships']:
            
            if relationship['Type'] == 'CHILD':
                
                for child_id in relationship['Ids']:
                    
                    word = blocks_map[child_id]
                    
                    if word['BlockType'] == 'WORD':
                        
                        text += word['Text'] + ' '
                        
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        
                        if word['SelectionStatus'] == 'SELECTED':
                            
                            text += 'X '

    return text
