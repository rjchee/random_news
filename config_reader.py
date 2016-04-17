import configparser

def read_configs():
    config = configparser.ConfigParser()
    config.read('config.ini')
    config.add_section('MODEL_WEIGHTS')
    for model_section in filter(lambda x : x.endswith('MODELS'), config.sections()):
        for model in config[model_section]:
            items = config[model_section][model].split(',')
            config['MODEL_WEIGHTS'][model] = items[1]
            config[model_section][model] = items[0]
    return config
