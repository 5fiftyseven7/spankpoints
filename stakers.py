import csv
import json
import sys
from web3 import Web3


def get_events(fromBlock, toBlock):
    spankbank = '0x1ECB60873E495dDFa2a13A8F4140e490dd574E6F'

    # [StakeEvent, SplitStakeEvent]
    topics = ['0x8bda6dd6519655ab1bc075f9bd7d863a6d6fef354ddae3a4b02bfe4053ce084b',
              '0x89f2292821f8c2270b88e93369feebc88dacba2a337f3fa7cd3a852e7af1a0d5']

    eventFilter = w3.eth.filter({
        "fromBlock": fromBlock,
        "toBlock": toBlock,
        "address": spankbank,
        "topics": [topics]
    })

    events = eventFilter.get_all_entries()
    for event in events:
        handle_event(event)


def handle_event(event):
    if event['topics'][0].hex() == '0x8bda6dd6519655ab1bc075f9bd7d863a6d6fef354ddae3a4b02bfe4053ce084b':
        # StakeEvent
        data = event['data'][2:]
        address = Web3.toChecksumAddress('0x' + data[24:64])
        start_period = int(data[64:128], 16)
        stakers[address] = start_period

    if event['topics'][0].hex() == '0x89f2292821f8c2270b88e93369feebc88dacba2a337f3fa7cd3a852e7af1a0d5':
        # SplitStakeEvent
        data = event['data'][2:]
        new_address = Web3.toChecksumAddress('0x' + data[64+24:128])
        splitters.append(new_address)


def get_splitter_periods():
    # get first period for splitters
    for staker in splitters:
        start_period = spankbank.functions.stakers(staker).call()[1]
        stakers[staker] = start_period


def spankpoints():
    # get first period points for every staker with ending period >= last_eligible_period
    staker_length = len(stakers.keys())
    count = 1
    for staker in stakers.keys():
        print(f'\rChecking staker {count} of {staker_length}', end='')
        ending_period = spankbank.functions.stakers(staker).call()[2]

        if ending_period >= last_eligible_period:
            # get first period points
            spankpoints = spankbank.functions.getSpankPoints(
                staker, stakers[staker]).call()
            stakers_points[staker] = spankpoints
        count += 1

    print()


def main():
    steps = 1000

    # get all staking addresses
    for i in range(start_block, end_block, steps):
        if i + 1 + steps > end_block:
            print(f'\rWriting blocks {i+1} to {end_block}', end='')
            get_events(i + 1, end_block)
        else:
            print(f'\rWriting blocks {i+1} to {i + steps}', end='')
            get_events(i + 1, i + steps)

    # get splitter starting periods
    get_splitter_periods()

    # get first period points per staker
    spankpoints()

    # sorting points dict
    sorted_stakers = {k: v for k, v in sorted(
        stakers_points.items(), key=lambda item: item[1], reverse=True)}

    with open('spankpoints.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        for k, v in sorted_stakers.items():
            writer.writerow((k, v))

    print(f'Total Stakers: {len(sorted_stakers.keys())}')


if __name__ == "__main__":
    w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

    spank_abi = json.load(open('spankbank_abi.json', 'r'))
    spankbank = w3.eth.contract(
        '0x1ECB60873E495dDFa2a13A8F4140e490dd574E6F', abi=spank_abi)

    start_block = 6276040 # before contract creation
    end_block = int(sys.argv[1])
    last_eligible_period = 28

    splitters = []
    stakers = {}  # staker: start_period
    stakers_points = {}  # staker: points

    main()
