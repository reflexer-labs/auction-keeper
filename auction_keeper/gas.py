# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2018 reverendus, bargst
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pprint import pformat
from typing import Optional
from web3 import Web3

from pygasprice_client import EthGasStation, EtherchainOrg, POANetwork, Etherscan, GasNow
from pyflex.gas import GasPrice, GeometricGasPrice, NodeAwareGasPrice


class UpdatableGasPrice(GasPrice):
    def __init__(self, gas_price: Optional[int]):
        assert isinstance(gas_price, int) or (gas_price is None)

        self.gas_price = gas_price

    def update_gas_price(self, gas_price: Optional[int]):
        assert isinstance(gas_price, int) or (gas_price is None)

        self.gas_price = gas_price

    def get_gas_price(self, time_elapsed: int) -> Optional[int]:
        return self.gas_price


class DynamicGasPrice(NodeAwareGasPrice):
    every_secs = 42
    def __init__(self, arguments, web3: Web3):
        assert isinstance(web3, Web3)
        self.gas_station = None
        self.fixed_gas = None
        self.web3 = web3
        if arguments.ethgasstation_api_key:
            self.gas_station = EthGasStation(refresh_interval=60, expiry=600, api_key=arguments.ethgasstation_api_key)
        elif arguments.etherchain_gas:
            self.gas_station = EtherchainOrg(refresh_interval=60, expiry=600)
        elif arguments.poanetwork_gas:
            self.gas_station = POANetwork(refresh_interval=60, expiry=600, alt_url=arguments.poanetwork_url)
        elif arguments.etherscan_gas:
            if arguments.etherscan_key:
                self.gas_station = Etherscan(refresh_interval=60, expiry=600, api_key=arguments.etherscan_key)
            else:
                self.gas_station = Etherscan(refresh_interval=60, expiry=600)
        elif arguments.gasnow_gas:
            if arguments.gasnow_app_name:
                self.gas_station = GasNow(refresh_interval=60, expiry=600, app_name=arguments.gasnow_app_name)
            else:
                self.gas_station = GasNow(refresh_interval=60, expiry=600)
        elif arguments.fixed_gas_price:
            self.fixed_gas = int(round(arguments.fixed_gas_price * self.GWEI))
        self.initial_multiplier = arguments.gas_initial_multiplier
        self.reactive_multiplier = arguments.gas_reactive_multiplier
        self.gas_maximum = int(round(arguments.gas_maximum * self.GWEI))
        if self.fixed_gas:
            assert self.fixed_gas <= self.gas_maximum

    def __del__(self):
        if self.gas_station:
            self.gas_station.running = False

    def get_gas_price(self, time_elapsed: int) -> Optional[int]:
        # start with fast price from the configured gas API
        fast_price = self.gas_station.fast_price() if self.gas_station else None

        # if API produces no price, or remote feed not configured, start with a fixed price
        if fast_price is None:
            if self.fixed_gas:
                initial_price = self.fixed_gas
            else:
                initial_price = self.get_node_gas_price()
        # otherwise, use the API's fast price, adjusted by a coefficient, as our starting point
        else:
            initial_price = int(round(self.get_node_gas_price() * self.initial_multiplier))

        return GeometricGasPrice(initial_price=initial_price,
                                 every_secs=DynamicGasPrice.every_secs,
                                 coefficient=self.reactive_multiplier,
                                 max_price=self.gas_maximum).get_gas_price(time_elapsed)

    def __str__(self):
        if self.gas_station:
            retval = f"{type(self.gas_station)} fast gas price with initial multiplier {self.initial_multiplier} "
        elif self.fixed_gas:
            retval = f"Fixed gas price {round(self.fixed_gas / self.GWEI, 1)} Gwei "
        else:
            retval = f"Node gas price (currently {round(self.get_node_gas_price() / self.GWEI, 1)} Gwei, "\
                    f"changes over time) with initial multiplier {self.initial_multiplier} "

        retval += f"and will multiply by {self.reactive_multiplier} every {DynamicGasPrice.every_secs}s " \
                  f"to a maximum of {round(self.gas_maximum / self.GWEI, 1)} Gwei"
        return retval

    def __repr__(self):
        return f"DynamicGasPrice({pformat(vars(self))})"
