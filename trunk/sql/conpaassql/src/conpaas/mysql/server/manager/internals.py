"""
Created on November, 2011

   This module contains internals of the ConPaaS MySQL Server. ConPaaS MySQL Server consists of several
   nodes with different roles
     
     * Manager node
     * Agent node(s)
        * Master
        * Slave(s)

   :platform: Linux, Debian
   :synopsis: Internals of ConPaaS MySQL Servers.
   :moduleauthor: Ales Cernivec <ales.cernivec@xlab.si> 

"""

from conpaas.log import create_logger
from conpaas.mysql.server.manager.config import Configuration, ManagerException,\
    E_ARGS_UNEXPECTED, ServiceNode, E_UNKNOWN, E_ARGS_MISSING, E_STATE_ERROR, E_ARGS_INVALID
from threading import Thread
from conpaas.mysql.client import agent_client
import time
import conpaas
import conpaas.mysql.server.manager
from conpaas.web.http import HttpErrorResponse, HttpJsonResponse

"""
Members describing state of the Manager node.
"""

S_INIT = 'INIT'
S_PROLOGUE = 'PROLOGUE'
S_RUNNING = 'RUNNING'
S_ADAPTING = 'ADAPTING'
S_EPILOGUE = 'EPILOGUE'
S_STOPPED = 'STOPPED'
S_ERROR = 'ERROR'

memcache = None
dstate = None
exposed_functions = {}
config = None
logger = create_logger(__name__)
iaas = None
managerServer = None
dummy_backend = None

class MySQLServerManager():
    """
    Initializes :py:attr:`config` using Config and sets :py:attr:`state` to :py:attr:`S_INIT`
    
    :param conf: Configuration file.
    :type conf: str    
    :param _dummy_backend: Useful for unit testing. What kind of backend are we using. False for none.
    :type conf: boolean
    
    """
    
    dummy_backend = False
    
    def __init__(self, conf, _dummy_backend=False):        
        logger.debug("Entering MySQLServerManager initialization")
        conpaas.mysql.server.manager.internals.config = Configuration(conf, _dummy_backend)         
        self.state = S_INIT
        self.dummy_backend = _dummy_backend
        conpaas.mysql.server.manager.internals.dummy_backend = _dummy_backend
        # TODO:
        self.__findAlreadyRunningInstances()
        logger.debug("Leaving MySQLServer initialization")
   
    def __findAlreadyRunningInstances(self):
        """
        Adds running instances of mysql agents to the list.
                
        """
        logger.debug("Entering __findAlreadyRunningInstances")
        list = iaas.listVMs()
        logger.debug('List obtained: ' + str(list))
        if self.dummy_backend:
            for i in list.values():
                conpaas.mysql.server.manager.internals.config.addMySQLServiceNode(i)
        else:
            for i in list.values():
                up = True
                try:
                    if i['ip'] != '':
                        logger.debug('Probing ' + i['ip'] + ' for state.')
                        ret = agent_client.get_server_state(i['ip'], 60000)                    
                        logger.debug('Returned query:' + str(ret))
                    else:
                        up = False
                except agent_client.AgentException as e: logger.error('Exception: ' + str(e))
                except Exception as e:
                    logger.error('Exception: ' + str(e))                
                    up = False
                if up:
                    logger.debug('Adding service node ' + i['ip'])
                    conpaas.mysql.server.manager.internals.config.addMySQLServiceNode(i)
        logger.debug("Exiting __findAlreadyRunningInstances")        

def expose(http_method):
    """
    Exposes GET and POSTS methods.
    
    :param func: Function to be exposed
    :type conf: function    
    :returns: A decorator to be used in the source code. 
    
    """
    def decorator(func):
        if http_method not in exposed_functions:
            exposed_functions[http_method] = {}
        exposed_functions[http_method][func.__name__] = func
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator

def wait_for_nodes(nodes, poll_interval=10):
    """
    Waits for nodes to get ready. It tries to call a function of the agent. If exception
    is thrown, wait for poll_interval seconds.
    
    :param nodes: a list of nodes
    :type nodes: array of nodes
    :param poll_intervall: how many seconds to wait. 10 secods is default value.
    :type poll_interfvall: int
    """
    logger.debug('wait_for_nodes: going to start polling')
    if conpaas.mysql.server.manager.internals.dummy_backend:
        pass
    else:        
        done = []
        while len(nodes) > 0:
            for i in nodes:
                up = True
                try:
                    if i['ip'] != '':
                        logger.debug('Probing ' + i['ip'] + ' for state.')
                        agent_client.get_server_state(i['ip'], 60000)
                    else:
                        up = False
                except agent_client.AgentException: pass
                except: up = False
                if up:
                    done.append(i)
            nodes = [ i for i in nodes if i not in done]
            if len(nodes):
                logger.debug('wait_for_nodes: waiting for %d nodes' % len(nodes))
                time.sleep(poll_interval)
                no_ip_nodes = [ i for i in nodes if i['ip'] == '' ]
                if no_ip_nodes:
                    logger.debug('wait_for_nodes: refreshing %d nodes' % len(no_ip_nodes))
                    refreshed_list = iaas.listVMs()
                    for i in no_ip_nodes:
                        i['ip'] = refreshed_list[i['id']]['ip']
        logger.debug('wait_for_nodes: All nodes are ready %s' % str(done))

def createServiceNodeThread (function, new_vm):
    """
    Waits for new VMs to awake.
     
    :param function: None, agent or manager.
    :type function: str
    :param new_vm: new VM's details.
    :type new_vm: array of str  
    """
    node_instances = []    
    vm=iaas.listVMs()[new_vm['id']]
    node_instances.append(vm)
    wait_for_nodes(node_instances)
    config.addMySQLServiceNode(new_vm)

#===============================================================================
# @expose('GET')
#'''
#    For each of the node from the list of the manager check that it is alive (in the list
#    returned by the ONE).
#'''
# def listServiceNodes(kwargs):
#    logger.debug("Entering listServiceNode")
#    if len(kwargs) != 0:
#        return {'opState': 'ERROR', 'error': ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message}
#    #dstate = memcache.get(DEPLOYMENT_STATE)    
#    vms = iaas.listVMs()
#    vms_mysql = config.getMySQLServiceNodes()
#    for vm in vms_mysql:
#        if not(vm.vmid in vms.keys()):
#            logger.debug('Removing instance ' + str(vm.vmid) + ' since it is not in the list returned by the listVMs().')
#            config.removeMySQLServiceNode(vm.vmid)         
#    #if dstate != S_RUNNING and dstate != S_ADAPTING:
#    #    return {'opState': 'ERROR', 'error': ManagerException(E_STATE_ERROR).message}    
#    #config = memcache.get(CONFIG)
#    logger.debug("Exiting listServiceNode")
#    return {
#          'opState': 'OK',
#          #'sql': [ serviceNode.vmid for serviceNode in managerServer.config.getMySQLServiceNodes() ]
#          #'sql': [ vms.keys() ]
#          'sql': [ [serviceNode.vmid, serviceNode.ip, serviceNode.port, serviceNode.state ] for serviceNode in config.getMySQLServiceNodes() ]
#    }
#===============================================================================

@expose('GET')
def list_nodes(kwargs):
    """
    HTTP GET method.
    Uses :py:meth:`IaaSClient.listVMs()` to get list of 
    all Service nodes. For each service node it gets it 
    checks if it is in servers list. If some of them are missing 
    they are removed from the list. Returns list of all service nodes.
       
    :returns: HttpJsonResponse - JSON response with the list of services
    :raises: HttpErrorResponse
        
    """    
    logger.debug("Entering list_nodes")
    if len(kwargs) != 0:
        return HttpErrorResponse(ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message)
    vms = iaas.listVMs()
    vms_mysql = config.getMySQLServiceNodes()
    for vm in vms_mysql:
        if not(vm.vmid in vms.keys()):
            logger.debug('Removing instance ' + str(vm.vmid) + ' since it is not in the list returned by the listVMs().')
            config.removeMySQLServiceNode(vm.vmid)  
    logger.debug("Exiting list_nodes")  
    _nodes = [ serviceNode.vmid for serviceNode in config.getMySQLServiceNodes() ]             
    return HttpJsonResponse({
        'serviceNode': _nodes,
        })

@expose('GET')
def get_node_info(kwargs):
    """
    HTTP GET method. Gets info of a specific node.

    :param param: serviceNodeId is a VMID of an existing service node.
    :type param: str
    :returns: HttpJsonResponse - JSON response with details about the node.
    :raises: ManagerException
        
    """    
    
    if 'serviceNodeId' not in kwargs: return HttpErrorResponse(ManagerException(E_ARGS_MISSING, 'serviceNodeId').message)
    serviceNodeId = kwargs.pop('serviceNodeId')
    if len(kwargs) != 0:
        return HttpErrorResponse(ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message)
    #for keys in config.serviceNodes.keys():
    #    if  keys
    if int(serviceNodeId) not in config.serviceNodes.keys(): return HttpErrorResponse(ManagerException(E_ARGS_INVALID , "serviceNodeId" , detail='Invalid "serviceNodeId"').message)
    serviceNode = config.serviceNodes[int(serviceNodeId)]
    return HttpJsonResponse({
            'serviceNode': {
                            'id': serviceNode.vmid,
                            'ip': serviceNode.ip,
                            'isRunningMySQL': serviceNode.isRunningMySQL
                            }
            })
    
'''Creates a new service node. 
@param function: None, "manager" or "agent". If None, empty image is provisioned. If "manager"
new manager is awaken and if the function equals "agent", new instance of the agent is 
provisioned.     
'''
#===============================================================================
# @expose('POST')
# def createServiceNode(kwargs):
#    if not(len(kwargs) in (0,1, 3)):
#        return {'opState': 'ERROR', 'error': ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message}    
#    if len(kwargs) == 0:
#        new_vm=iaas.newInstance(None)
#        Thread(target=createServiceNodeThread(None, new_vm)).start()
#    elif len(kwargs) == 1:
#        new_vm=iaas.newInstance(kwargs['function'])
#        Thread(target=createServiceNodeThread(kwargs['function'], new_vm)).start()
#    else:
#        pass
#    return {
#          'opState': 'OK',
#          'sql': [ new_vm['id'] ]
#    }
#===============================================================================

@expose('POST')
def add_nodes(kwargs):
    """
    HTTP POST method. Creates new node and adds it to the list of existing nodes in the manager. Makes internal call to :py:meth:`createServiceNodeThread`.

    :param kwargs: string describing a function (agent).
    :type param: str
    :returns: HttpJsonResponse - JSON response with details about the node.
    :raises: ManagerException
        
    """ 
    
    function = None
    if 'function' in kwargs:
        #if not isinstance(kwargs['function'], str):
        #    logger.error("Expected a string value for function")
        #    return HttpErrorResponse(ManagerException(E_ARGS_INVALID, detail='Expected a string value for "function"').message)
        function = str(kwargs.pop('function'))        
    #if not(len(kwargs) in (0,1, 3)):
    #    return {'opState': 'ERROR', 'error': ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message}    
    new_vm=iaas.newInstance(function)
    Thread(target=createServiceNodeThread(function, new_vm)).start()
    return HttpJsonResponse({
        'serviceNode': {
                        'id': new_vm['id'],
                        'ip': new_vm['ip'],
                        'state': new_vm['state'],
                        'name': new_vm['name']
                        }
         })

@expose('POST')
def create_replica(kwargs):
    """ 
    HTTP POST method.Creating a service replication.   
    
    """
    if not(len(kwargs) in (2)):
        return {'opState': 'ERROR', 'error': ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message}    
    new_vm=iaas.newInstance('agent')
    master_id=kwargs['master_id']
    createServiceNodeThread('agent', new_vm)    
    '''new_vm is a new replica instance
    '''
    '''TODO: insert code for initializing a replica master'''
    '''TODO: insert code for initializing a replica client'''
    
    return {
          'opState': 'OK',
          'sql': [ new_vm['id'] ]
    }

#===============================================================================
# @expose('POST')
# def deleteServiceNode(kwargs):
#    if len(kwargs) != 1:
#        return {'opState': 'ERROR', 'error': ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message}
#    logger.debug('deleteServiceNode ' + str(kwargs['id']))
#    if iaas.killInstance(kwargs['id']):
#        config.removeMySQLServiceNode(kwargs['id'])
#    '''TODO: If false, return false response.
#    '''
#    return {
#          'opState': 'OK'    
#    }
#===============================================================================

@expose('POST')
def remove_nodes(kwargs):
    """
    HTTP POST method. Deletes specific node from a pool of agent nodes. 

    :param kwargs: string identifying a node.
    :type param: str
    :returns: HttpJsonResponse - JSON response with details about the node. OK if evrything went well. ManagerException if something went wrong.
    :raises: ManagerException
        
    """ 
    
    logger.debug("Entering delete_nodes")
    if 'serviceNodeId' not in kwargs: return HttpErrorResponse(ManagerException(E_ARGS_MISSING, 'serviceNodeId').message)
    serviceNodeId = int(kwargs.pop('serviceNodeId'))
    if len(kwargs) != 0:
        return HttpErrorResponse(ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message)
    if serviceNodeId not in config.serviceNodes: return HttpErrorResponse(ManagerException(E_ARGS_INVALID, "serviceNodeId", detail='Invalid "serviceNodeId"').message)
    serviceNode = config.serviceNodes[serviceNodeId]      
    logger.debug('deleteServiceNode ' + str(serviceNodeId))
    if iaas.killInstance(serviceNodeId):
        config.removeMySQLServiceNode(serviceNodeId)
    '''TODO: If false, return false response.
    '''
    return HttpJsonResponse({'result': 'OK'})

@expose('GET')
def get_service_info(kwargs):
    """    
    HTTP GET method. Returns the current state of the manager. 

    :returns: HttpJsonResponse - JSON response with the description of the state.
    :raises: ManagerException
        
    """ 
    
    logger.debug("Entering get_service_info")
    try: 
        logger.debug("Leaving get_service_info")
        return HttpJsonResponse({
            'service': {
                            'state':managerServer.state                        
                        }
            })
    except Exception as e:
        ex = ManagerException(E_UNKNOWN, detail=e)
        logger.exception(e)
        logger.debug('Leaving get_service_info')
        return HttpJsonResponse({'result': 'OK'})
 
#===============================================================================
# @expose('GET')
# def get_node_info( kwargs):
#    logger.debug("Entering get_node_info")
#    if 'serviceNodeId' not in kwargs: return HttpErrorResponse(ManagerException(E_ARGS_MISSING, 'serviceNodeId').message)
#    serviceNodeId = kwargs.pop('serviceNodeId')
#    if len(kwargs) != 0:
#        return HttpErrorResponse(ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message)
#    
#    config = self._configuration_get()
#    if serviceNodeId not in config.serviceNodes: return HttpErrorResponse(ManagerException(E_ARGS_INVALID, detail='Invalid "serviceNodeId"').message)
#    serviceNode = config.serviceNodes[serviceNodeId]
#    return HttpJsonResponse({
#            'serviceNode': {
#                            'id': serviceNode.vmid,
#                            'ip': serviceNode.ip,
#                            'isRunningProxy': serviceNode.isRunningProxy,
#                            'isRunningWeb': serviceNode.isRunningWeb,
#                            'isRunningBackend': serviceNode.isRunningBackend,
#                            'isRunningMySQL': serviceNode.isRunningBackend,
#                            }
#            })
#===============================================================================

@expose('POST')
def set_up_replica_master(params):
    """
    HTTP POST method. Sets up a replica master node 

    :param id: new replica master id.
    :type param: dict
    :returns: HttpJsonResponse - JSON response with details about the new node. ManagerException if something went wrong.
    :raises: ManagerException
        
    """ 
    
    logger.debug("Entering set_up_replica_master")
    if len(params) != 1:
        return {'opState': 'ERROR', 'error': ManagerException(E_ARGS_UNEXPECTED, params.keys()).message}
    new_master_id = params['id']
    new_master_ip = ''
    new_master_port = ''
    for node in config.getMySQLServiceNodes():
        if new_master_id == node.id:
            new_master_ip=node.ip
            new_master_port=node.port
    agent_client.set_up_replica_master(new_master_ip, new_master_port)
    logger.debug("Exiting set_up_replica_master")
    pass

@expose('POST')
def set_up_replica_slave(params):
    """
    HTTP POST method. Sets up a replica slave node 

    :param id: new replica slave id.
    :type param: dict
    :returns: HttpJsonResponse - JSON response with details about the new node. ManagerException if something went wrong.
    :raises: ManagerException
        
    """ 
    
    logger.debug("Entering set_up_replica_slave")
    if len(params) != 5:
        return {'opState': 'ERROR', 'error': ManagerException(E_ARGS_UNEXPECTED, params.keys()).message}
    _id = params['id']
    _host = ''
    _port = ''
    for node in config.getMySQLServiceNodes():
        if _id == node.id:
            _host=node.ip
            _port=node.port
    master_host = params['master_host']
    master_log_file = params['master_log_file']
    master_log_pos = params['master_log_pos']
    slave_server_id = params['slave_server_id']
    agent_client.set_up_replica_slave(_host, _port, master_host, master_log_file, master_log_pos, slave_server_id)
    logger.debug("Exiting set_up_replica_slave")
    pass

@expose('POST')
def shutdown(self, kwargs):
    """
    HTTP POST method. Shuts down the manager service. 

    :returns: HttpJsonResponse - JSON response with details about the status of a manager node: . ManagerException if something went wrong.
    :raises: ManagerException
        
    """ 
    if len(kwargs) != 0:
        return HttpErrorResponse(ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message)
    
    dstate = self._state_get()
    if dstate != self.S_RUNNING:
        return HttpErrorResponse(ManagerException(E_STATE_ERROR).message)
    
    config = self._configuration_get()
    self._state_set(self.S_EPILOGUE, msg='Shutting down')
    Thread(target=self.do_shutdown, args=[config]).start()
    return HttpJsonResponse({'state': self.S_EPILOGUE})

@expose('GET')
def get_service_performance(self, kwargs):
    ''' HTTP GET method. Placeholder for obtaining performance metrics.
     
    :param kwargs: Additional parameters.
    :type kwargs: dict 
    :returns:  HttpJsonResponse -- returns metrics
    
    '''
    
    if len(kwargs) != 0:
        return HttpErrorResponse(ManagerException(E_ARGS_UNEXPECTED, kwargs.keys()).message)
    return HttpJsonResponse({
            'request_rate': 0,
            'error_rate': 0,
            'throughput': 0,
            'response_time': 0,
            })