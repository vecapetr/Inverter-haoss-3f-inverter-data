const tuya = require('zigbee-herdsman-converters/lib/tuya');
const exposes = require('zigbee-herdsman-converters/lib/exposes');
const e = exposes.presets;
const ea = exposes.access;

module.exports = {
    fingerprint: [
        {
            modelID: 'TS0601',
            manufacturerName: '_TZE284_tgeqdjgk',
        },
    ],
    model: 'TS0601_knob_dimmer_switch',
    vendor: 'TuYa',
    description: 'Dimmer knob with two lights and adjustment mode (brightness/color_temp)',

    // Přehled odchozích zpráv
    fromZigbee: [
        tuya.fz.datapoints,
    ],

    // Přehled příkazů směrem do zařízení
    toZigbee: [
        {
            key: ['adjustment_mode'],
            convertSet: async (entity, key, value, meta) => {
                const mode = value === 'brightness' ? 0 : 1;
                await tuya.sendDataPointEnum(entity, 105, mode);
                return { state: { adjustment_mode: value } };
            },
        },
        tuya.tz.datapoints, // fallback
    ],

    // Nastavení expozic pro Home Assistant
    exposes: [
        e.binary('light_1', ea.STATE_SET, 'ON', 'OFF'),
        e.binary('light_2', ea.STATE_SET, 'ON', 'OFF'),
        e.binary('state', ea.STATE_SET, 'ON', 'OFF').withDescription('Global state'),
        e.numeric('brightness', ea.STATE_SET).withValueMin(0).withValueMax(100).withDescription('Brightness'),
        e.numeric('color_temp', ea.STATE_SET).withValueMin(0).withValueMax(1000).withDescription('Color temperature'),
        e.enum('adjustment_mode', ea.STATE_SET, ['brightness', 'color_temp']).withDescription('Brightness or color temperature adjustment'),
    ],

    meta: {
    tuyaDatapoints: [
        [102, 'state', tuya.valueConverter.onOff],
        [103, 'brightness', tuya.valueConverter.divideBy10],
        [107, 'color_temp', tuya.valueConverter.raw],
        [105, 'adjustment_mode', {
            from: (val) => val === 0 ? 'brightness' : 'color_temp',
            to: (val) => val === 'brightness' ? 0 : 1,
        }],
        [121, 'light_1', tuya.valueConverter.onOff],
        [122, 'light_2', tuya.valueConverter.onOff],
    ],
    },


    configure: tuya.configureMagicPacket,

    endpoint: (device) => ({
        'default': 1,
    }),
};
