// This code is distributed under the GNU General Public License (see
// THE_GENERAL_GNU_PUBLIC_LICENSE.txt for extending this information).
// Copyright (C) 2015, the P2PSP team.
// http://www.p2psp.org

#ifndef P2PSP_CORE_TRUSTED_PEER_H
#define P2PSP_CORE_TRUSTED_PEER_H

#include <vector>
#include <boost/asio.hpp>

#include "malicious_peer.h"
#include "../util/trace.h"

namespace p2psp {

using namespace boost::asio;

class TrustedPeer : public MaliciousPeer {
 protected:
  static const int kPassNumber = 10;
  static const int kSamplingEffort = 2;
  int counter_;
  int next_sampled_index_;
  bool check_all_;
  ip::udp::endpoint current_sender_;

 public:
  TrustedPeer(){};
  ~TrustedPeer(){};
  virtual void Init();
};
}

#endif  // P2PSP_CORE_TRUSTED_PEER_H
