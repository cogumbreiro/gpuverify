//===-----------------------------------------------------------------------==//
//
//                GPUVerify - a Verifier for GPU Kernels
//
// This file is distributed under the Microsoft Public License.  See
// LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//


﻿using System;
using System.Diagnostics;
using Microsoft.Boogie;

namespace GPUVerify
{
  public class GPUVerifyCruncherCommandLineOptions : CommandLineOptions
  {
    public string ArrayToCheck = null;
    public bool NoSourceLocInfer = false;
    public bool OnlyIntraGroupRaceChecking = false;
    public bool DebugGPUVerify = false;

    public GPUVerifyCruncherCommandLineOptions() :
      base("GPUVerify", "GPUVerify kernel analyser")
    { }

    protected override bool ParseOption(string name, CommandLineOptionEngine.CommandLineParseState ps)
    {
      if (name == "debugGPUVerify") {
        DebugGPUVerify = true;
        return true;
      }

      if (name == "array") {
        if (ps.ConfirmArgumentCount(1)) {
          ArrayToCheck = ToInternalArrayName(ps.args[ps.i]);
        }
        return true;
      }

      if (name == "noSourceLocInfer") {
        NoSourceLocInfer = true;
        return true;
      }

      if (name == "onlyIntraGroupRaceChecking") {
        OnlyIntraGroupRaceChecking = true;
        return true;
      }

      return base.ParseOption(name, ps);  // defer to superclass
    }

    private string ToInternalArrayName(string arrayName)
    {
      return "$$" + arrayName;
    }

    internal string ToExternalArrayName(string arrayName)
    {
      Debug.Assert(arrayName.StartsWith("$$"));
      return arrayName.Substring("$$".Length);
    }
  }
}
