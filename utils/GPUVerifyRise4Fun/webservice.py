# vim: set sw=2 ts=2 softtabstop=2 expandtab:
from meta_data import *
from flask import Flask, jsonify, url_for, request, abort
from socket import gethostname
import logging
import pprint
from SourceCodeSanitiser import SourceCodeSanitiser
import traceback
import pprint


app = Flask(__name__)

#Load configuration from config.py
app.config.from_object('config')

#Internal logger
_logging = logging.getLogger(__name__)

cudaMetaData = {}
openclMetaData = {} 
_tool = None
_sourceCodeSanitiser = None

# This is not ideal, we delay initialisation
# until the first request which could slow
# down the first request. However this is
# the only way I could find to perform initilisation
# after forking in Tornado (required so each
# KernelCounterObserver can initialise itself 
# correctly)
@app.before_first_request
def init():
  # Pre-compute metadata information
  global cudaMetaData , openclMetaData, _gpuverifyObservers, _tool, _sourceCodeSanitiser
  cudaMetaData = CUDAMetaData(app.config['SRC_ROOT'])
  openclMetaData = OpenCLMetaData(app.config['SRC_ROOT'])

  # Create GPUVerify tool instance
  _tool = gvapi.GPUVerifyTool(app.config['GPUVERIFY_ROOT_DIR'], app.config['GPUVERIFY_TEMP_DIR'])

  # Create Source code sanitiser
  _sourceCodeSanitiser = SourceCodeSanitiser()

  #Register observers
  from observers.kernelcounter import KernelCounterObserver
  from observers.kernelrecorder import KernelRecorderObserver
  _tool.registerObserver( KernelCounterObserver(app.config['KERNEL_COUNTER_PATH']) )
  if app.config['LOGGED_KERNELS_DIR'] != None:
    _tool.registerObserver( KernelRecorderObserver(app.config['LOGGED_KERNELS_DIR']) )

#Setup routing
@app.errorhandler(404)
def notFound(error):
  return jsonify({ 'Error': error.description} ), 404
  

@app.route('/<lang>/metadata', methods=['GET'])
def getToolInfo(lang):
  if not checkLang(lang):
    abort(400)


  if lang == CUDAMetaData.folderName:
    metaData = cudaMetaData.metadata
  else:
    metaData = openclMetaData.metadata

  # Patch meta data with image URL
  metaData['InstitutionImageUrl'] = url_for('static', filename='imperial-college-logo.png', _external=True)

  # Do not have proper privacy policy/Terms of use URL for now
  # Patch meta data with privacy policy URL
  # metaData['PrivacyUrl'] = url_for('static', filename='privacy-policy.html', _external=True)

  # Patch meta data with terms of use URL
  # metaData['TermsOfUseUrl'] = url_for('static', filename='terms-of-use.html', _external=True)
  return jsonify(metaData)

@app.route('/<lang>/language', methods=['GET'])
def getLanguageSyntaxDefinition(lang):
  if not checkLang(lang):
    abort(400)

  if lang == CUDAMetaData.folderName:
    metaData = cudaMetaData
  else:
    metaData = openclMetaData

  if metaData.languageSyntax != None:
    return jsonify(metaData.languageSyntax)
  else:
    return jsonify({'Error':'Language syntax definition is not availabe for ' + metaData.folderName})

@app.route('/<lang>/run', methods=['POST'])
def runGpuverify(lang):
  if not checkLang(lang):
    abort(400)
  
  if not request.json:
    abort(400)


  source = request.json['Source']
  _logging.debug('Received request:\n' + pprint.pformat(request.json))

  # Sanitise the source code
  assert _sourceCodeSanitiser != None
  source = _sourceCodeSanitiser.sanitise( source )

  # Assume _tool already initialised
  assert _tool != None

  returnMessage = { 'Version':None, 
                    'Outputs': [
                                 { "MimeType":"text/plain",
                                   "Value":None
                                 }
                               ]   
                  }
  returnCode=None
  toolMessage=None
  dimMessage=""
  ignoredArgs=[]
  safeArgs=[]
  try:
    _tool.filterCmdArgs(source, safeArgs, ignoredArgs, app.config['GPUVERIFY_DEFAULT_ARGS'])

    if lang == CUDAMetaData.folderName:
      returnMessage['Version'] = cudaMetaData.metadata['Version']
      (returnCode, toolMessage) = _tool.runCUDA(source, 
                                                safeArgs,
                                                timeout=app.config['GPUVERIFY_TIMEOUT']
                                               )
                                               

    else:
      returnMessage['Version'] = openclMetaData.metadata['Version']

      (returnCode, toolMessage) = _tool.runOpenCL(source, 
                                                  safeArgs,
                                                  timeout=app.config['GPUVERIFY_TIMEOUT']
                                                 )

    # We might have an extra message to show.
    extraHelpMessage=""
    if gvapi.helpMessage[returnCode] != "":
      extraHelpMessage = gvapi.helpMessage[returnCode] + '\n' 

    toolMessage = filterToolOutput(toolMessage)

    # If the source code sanitiser issued warnings show them.
    if len(_sourceCodeSanitiser.getWarnings()) != 0:
      warnings = reduce( lambda lineA, lineB: lineA + '\n' + lineB + '\n',
                         map( lambda m : 'Warning: ' + m,
                              _sourceCodeSanitiser.getWarnings()
                            )
                       )
      toolMessage = warnings + '\n\n' + toolMessage

    # If we have ignored command line arguments warn the user about this
    if len(ignoredArgs) != 0:
      warning = 'Warning ignored command line option(s):\n{0}\n\n'.format(pprint.pformat(ignoredArgs))
      toolMessage = warning + toolMessage


    returnMessage['Outputs'][0]['Value'] = (extraHelpMessage + toolMessage)

  except Exception as e:
    returnMessage['Outputs'][0]['Value'] = 'Web service error:' + str(e)
    _logging.error('Exception occured:\n' + traceback.format_exc())

  _sourceCodeSanitiser.removeWarnings() # Do not hold on to warnings
  _logging.debug('Sending responce:\n' + pprint.pformat(returnMessage))
  return jsonify(returnMessage)
    

@app.route('/help', methods=['GET'])
def getGPUVerifyHelp():
  (returnCode, toolMessage) = _tool.runOpenCL("",["--help"]);

  response = {'help': toolMessage }
  return jsonify(response)


def checkLang(lang):
  if lang in BasicMetaData.registeredLanguage:
    return True
  else:
    return False

def filterToolOutput(toolMessage):
    # Strip out any leading new lines from tool output.
    for (index,char) in enumerate(toolMessage):
      if char != '\n':
        toolMessage=toolMessage[index:]
        break

    # Remove any absolute paths for files (e.g. tools and source files) and 
    # replace with just the basename.
    # Microsoft in their "infinite" wisdom use flags like "/noinfer"
    # So we have to be careful when filtering.

    dirOrFileRegex = r'[a-z0-9_.-]+'
    regex = r'/(' +dirOrFileRegex+ r'/)+(' + dirOrFileRegex + r')\b'
    _logging.debug('Using regex:{0}'.format(regex))
    (output, n) = re.subn(regex, r'\2', toolMessage, flags=re.IGNORECASE)
    _logging.info('Filtering output. {0} replacements were made.'.format(n))
    _logging.debug('Replacing:\n{0}\nWith:\n{1}'.format(toolMessage, output))
    return output



if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  import argparse
  parser = argparse.ArgumentParser(description='Run Development version of GPUVerifyRise4Fun web service')
  parser.add_argument('-p', '--port', type=int, default=55000, help='Port to use. Default %(default)s')
  parser.add_argument('-d', '--debug', action='store_true',default=False, help='Use Flask Debug mode and show debugging output. Default %(default)s')
  parser.add_argument('--public', action='store_true', default=False, help='Make publically accessible. Default %(default)s')
  parser.add_argument('-s','--server-name', type=str, default='localhost' , help='Set server hostname. This is ignored is --public is used. Default "%(default)s"')

  args = parser.parse_args()


  if args.debug:
    print("Using Debug mode")
    logging.getLogger().setLevel(logging.DEBUG)
  
  # extra options
  options = { }
  if args.public:
    options['host'] = '0.0.0.0'
    app.config['SERVER_NAME'] = gethostname() + ':' + str(args.port)
  else:
    app.config['SERVER_NAME'] = args.server_name + ':' + str(args.port)

  print("Setting SERVER_NAME to " + app.config['SERVER_NAME'])

  app.run(debug=args.debug, port=args.port, **options)
