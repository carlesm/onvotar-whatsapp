import re
import logging
from yowsup.layers.interface import YowInterfaceLayer
from yowsup.layers.interface import ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities.message_text import TextMessageProtocolEntity
from onvotar import calculate

logger = logging.getLogger()

_DNI_PATTERN = re.compile('^([0-9]{8}[^A-Z]?[A-Z])$')
_DOB_PATTERN = re.compile('^([0-9]{8})$')
_ZIP_PATTERN = re.compile('^([0-9]{5})$')

DEFAULT_ERR = (
    'Per conèixer el teu col·legi electoral, '
    'envia un missatge amb les teves dades '
    'separades per espais i '
    'fent servir aquest format: \n'
    'DNI DATA_NAIXEMENT CODI_POSTAL\n\n'
    'Exemple:\n00001714N 01/10/2017 01234'
)

DATA_DISCLAIMER = (
    'Aquest bot utilitza la mateixa tecnologia que '
    'la web original oficial del Referèndum.\n'
    'No desa ni mostra als autors cap dada sensible.'
)


class EchoLayer(YowInterfaceLayer):

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        short_num = messageProtocolEntity.getFrom(False)[:3]
        hashed_num = hash(messageProtocolEntity.getFrom(False))

        if messageProtocolEntity.getType() == 'text':
            logger.info(
                'Message recieved from %s... (%s)', short_num, hashed_num)
            self.onTextMessage(messageProtocolEntity)
        else:
            logger.info(
                'Ignoring media recieved from %s... (%s)',
                short_num,
                hashed_num
            )

        self.toLower(messageProtocolEntity.ack())
        self.toLower(messageProtocolEntity.ack(True))

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        self.toLower(entity.ack())

    def onTextMessage(self, messageProtocolEntity):
        text = messageProtocolEntity.getBody()
        try:
            dni, date, cp = self._check_input_data(text)
        except ValueError as e:
            response = str(e)
            if response == DEFAULT_ERR:
                logger.info('Error: No hi ha 3 dades')
            else:
                logger.info('Error: %s', response)
        else:
            result = calculate(dni, date, cp)
            if result:
                response = (
                    '{}\n{}\n{}\n\n'
                    'Districte: {}\n'
                    'Secció: {}\n'
                    'Mesa: {}'
                ).format(*result)
                logger.info(
                    'Punt de votacio retornat correctament. %s %s',
                    date[:4], cp
                )
            else:
                response = (
                    'Alguna de les dades entrades no és correcta.\n'
                    'Revisa-les, si us plau.'
                )
                logger.info('Bon format pero dades incorrectes')

        logger.info('---')

        self.toLower(TextMessageProtocolEntity(
            response,
            to=messageProtocolEntity.getFrom()
        ))
        
        # SPECIAL: DISCLAIMER
        if response == DEFAULT_ERR:
            self.toLower(TextMessageProtocolEntity(
                DATA_DISCLAIMER,
                to=messageProtocolEntity.getFrom()
            ))

    def _check_input_data(self, text):
        splitted = text.split(' ')
        if len(splitted) != 3:
            raise ValueError(DEFAULT_ERR)
        
        raw_dni, raw_date, cp = splitted

        dni = raw_dni.upper().replace(' ','').replace('-','')
        match = _DNI_PATTERN.match(dni)
        if not match:
            raise ValueError('Revisa el format del DNI')

        date = raw_date.upper().replace(' ','').replace('/','')
        match = _DOB_PATTERN.match(date)
        if not match:
            raise ValueError('Revisa el format de la data de naixement')
        date = date[-4:]+date[2:4]+date[:2]
        
        match = _ZIP_PATTERN.match(cp)
        if not match:
            raise ValueError('Revisa el format del codi postal')

        return dni, date, cp
