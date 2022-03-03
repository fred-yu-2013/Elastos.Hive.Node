# -*- coding: utf-8 -*-

"""
hive_hub module to save hive node list in hive hub website.
"""
from flask import Blueprint

from src.modules.hivehub.hivehub import HiveHub
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import rqargs, params

blueprint = Blueprint('hive_hub', __name__)
hive_hub: HiveHub = None


def init_app(app):
    """ This will be called by application initializer. """
    global hive_hub
    hive_hub = HiveHub()
    app.register_blueprint(blueprint)


@blueprint.route('/api/hivehub/nodes', methods=['GET'])
def get_nodes():
    """ query nodes by nid(_id) or owner_did
    Return: [{
        "nid": "jlaksjdflkjasdlkfj001",
        "name": "hive node 节点A",
        "created": "2021-11-09 21:00:32",
        "ip": "192.115.24.2",
        "owner_did": owner_did,
        "area": "加拿大 安大略省 多伦多市",
        "email": "1234456789@gamil.com",
        "url": hive1_url,
        "remark": "区块链是一个信息技术领域的术语。从本质上讲，它是一个共享数据库，存储于其中的数据或信息，具有“不可伪造”“全程留痕”“可以追溯”“公开透明”“集体维护”等特征。基于这些特征，区块链技术奠定了坚实的“信任”基础，创造了可靠的“合作”机制，具有广阔的运用前景。"
    }, {
        "nid": "jlaksjdflkjasdlkfj002",
        "name": "hive node 节点B",
        "created": "2021-11-09 21:00:32",
        "ip": "192.115.24.2",
        "owner_did": "did:elastos:srgsve5h5yvnwi5yh4hyg2945hvwq0tq",
        "area": "加拿大 安大略省 多伦多市",
        "email": "1234456789@gamil.com",
        "url": hive1_url,
        "remark": "区块链是一个信息技术领域的术语。从本质上讲，它是一个共享数据库，存储于其中的数据或信息，具有“不可伪造”“全程留痕”“可以追溯”“公开透明”“集体维护”等特征。基于这些特征，区块链技术奠定了坚实的“信任”基础，创造了可靠的“合作”机制，具有广阔的运用前景。"
    }]
    """
    nid, msg = rqargs.get_str('nid')
    owner_did, msg = rqargs.get_str('owner_did')
    return hive_hub.get_nodes(nid, owner_did)


@blueprint.route('/api/hivehub/node', methods=['POST'])
def add_node():
    """ Add node by `node` document
    Example: {
        "nid": "jlaksjdflkjasdlkfj001",
        "name": "hive node 节点A",
        "created": "2021-11-09 21:00:32",
        "ip": "192.115.24.2",
        "owner_did": owner_did,
        "area": "加拿大 安大略省 多伦多市",
        "email": "1234456789@gamil.com",
        "url": hive1_url,
        "remark": "区块链是一个信息技术领域的术语。从本质上讲，它是一个共享数据库，存储于其中的数据或信息，具有“不可伪造”“全程留痕”“可以追溯”“公开透明”“集体维护”等特征。基于这些特征，区块链技术奠定了坚实的“信任”基础，创造了可靠的“合作”机制，具有广阔的运用前景。"
    }
    """
    node, msg = params.get_dict('node')
    if not node or msg:
        return InvalidParameterException(msg=msg).get_error_response()
    return hive_hub.add_node(node)
